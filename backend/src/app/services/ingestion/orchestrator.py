"""Ingestion orchestrator - idempotent full flow."""

import hashlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.models import Chunk, File, IngestionLog, Parent, Project
from app.db.session import get_db
from app.services.ingestion.image_pipeline import find_parent_for_image, process_image_blocks
from app.services.parsing.base import ImageBlock, SourceType
from app.services.parsing.docx_parser import DocxParser
from app.services.parsing.pdf_parser import PdfParser
from app.services.parsing.pptx_parser import PptxParser


@dataclass
class IngestionResult:
    """Result of ingestion."""

    skipped: bool = False
    file_id: str = ""
    parents_created: int = 0
    chunks_created: int = 0
    error: str | None = None


def _get_parser(source_type: str):
    if source_type == "pdf":
        return PdfParser()
    if source_type == "pptx":
        return PptxParser()
    if source_type == "docx":
        return DocxParser()
    raise ValueError(f"Unsupported source_type: {source_type}")


def _get_chunking_policy():
    from app.services.indexing.chunking import (
        HybridChunkingPolicy,
        SemanticChunkingPolicy,
        StructureFixedChunkingPolicy,
    )

    settings = get_settings()
    policy_name = settings.chunking_policy
    if policy_name == "structure_fixed":
        return StructureFixedChunkingPolicy(
            target_tokens=settings.target_tokens,
            overlap_tokens=settings.overlap_tokens,
            hard_max_tokens=settings.hard_max_tokens,
        )
    if policy_name == "semantic":
        return SemanticChunkingPolicy(
            threshold=settings.semantic_threshold,
        )
    return HybridChunkingPolicy(
        semantic_enabled_min_tokens=settings.semantic_enabled_min_tokens,
        semantic_threshold=settings.semantic_threshold,
    )


def ingest_file(
    project_id: str,
    file_bytes: bytes,
    filename: str,
    source_type: str,
    index_version: str,
    file_id: str | None = None,
) -> IngestionResult:
    """
    Idempotent ingestion. Skip if doc_hash already ingested for project+version.
    """
    doc_hash = hashlib.sha256(file_bytes).hexdigest()
    file_id = file_id or str(uuid.uuid4())
    db = get_db()
    try:
        # Idempotency check
        existing = (
            db.query(IngestionLog)
            .filter(
                IngestionLog.project_id == project_id,
                IngestionLog.doc_hash == doc_hash,
                IngestionLog.index_version == index_version,
            )
            .first()
        )
        if existing:
            return IngestionResult(skipped=True, file_id=existing.file_id)

        # Ensure project exists
        proj = db.query(Project).filter(Project.project_id == project_id).first()
        if not proj:
            db.add(Project(project_id=project_id))
            db.commit()

        # Parse
        parser = _get_parser(source_type)
        blocks = parser.parse(file_bytes, filename)

        # Build parents
        policy = _get_chunking_policy()
        parents = policy.build_parents(blocks, source_type)

        # Image pipeline - find parent for each image, process
        image_blocks_with_parent: list[tuple[ImageBlock, str]] = []
        for b in blocks:
            if isinstance(b, ImageBlock):
                pid = find_parent_for_image(b, parents)
                if pid:
                    image_blocks_with_parent.append((b, pid))
        image_chunks = process_image_blocks(image_blocks_with_parent)

        # Build children from chunking
        all_chunks: list[Any] = []
        for parent in parents:
            children = policy.build_children(parent)
            all_chunks.extend(children)
        all_chunks.extend(image_chunks)

        # Store parents
        for p in parents:
            db.add(
                Parent(
                    parent_id=p.parent_id,
                    project_id=project_id,
                    file_id=file_id,
                    parent_type=p.parent_type,
                    loc=p.loc.to_dict(),
                    parent_text=p.parent_text,
                    seq_start=p.seq_start,
                    seq_end=p.seq_end,
                    index_version=index_version,
                    doc_hash=doc_hash,
                )
            )

        # Store file if not exists (e.g. from upload)
        existing_file = db.query(File).filter(File.file_id == file_id).first()
        if not existing_file:
            db.add(
                File(
                    file_id=file_id,
                    project_id=project_id,
                    filename=filename,
                    doc_hash=doc_hash,
                    source_type=source_type,
                )
            )

        # Embed and upsert vectors
        from app.services.providers.registry import get_embedding_provider, get_vector_store_adapter
        from app.services.providers.base import VectorRecord

        embedder = get_embedding_provider()
        vs = get_vector_store_adapter()
        texts = [c.embedding_text for c in all_chunks]
        if texts:
            vectors = embedder.embed(texts)
            records = [
                VectorRecord(
                    chunk_id=c.chunk_id,
                    vector=vec,
                    project_id=project_id,
                    file_id=file_id,
                    parent_id=c.parent_id,
                    chunk_type=c.chunk_type,
                    chunk_text=c.chunk_text,
                    loc=c.loc,
                    index_version=index_version,
                    doc_hash=doc_hash,
                )
                for c, vec in zip(all_chunks, vectors)
            ]
            vs.upsert(records)

        # Store chunk metadata in DB
        for c in all_chunks:
            db.add(
                Chunk(
                    chunk_id=c.chunk_id,
                    project_id=project_id,
                    file_id=file_id,
                    parent_id=c.parent_id,
                    chunk_type=c.chunk_type,
                    chunk_text=c.chunk_text,
                    embedding_text=c.embedding_text,
                    seq_start=c.seq_start,
                    seq_end=c.seq_end,
                    loc=c.loc,
                    chunk_policy=c.chunk_policy,
                    boundary_signals=c.boundary_signals,
                    policy_version=c.policy_version,
                    index_version=index_version,
                    doc_hash=doc_hash,
                )
            )

        # Idempotency log
        db.add(
            IngestionLog(
                project_id=project_id,
                file_id=file_id,
                doc_hash=doc_hash,
                index_version=index_version,
            )
        )
        db.commit()
        return IngestionResult(
            file_id=file_id,
            parents_created=len(parents),
            chunks_created=len(all_chunks),
        )
    except Exception as e:
        db.rollback()
        return IngestionResult(file_id=file_id, error=str(e))
    finally:
        db.close()
