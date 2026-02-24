"""Default VectorStoreAdapter - in-memory with optional JSON persistence."""

import json
import math
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services.providers.base import (
    SearchHit,
    VectorRecord,
    VectorStoreAdapter,
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1e-10
    norm_b = math.sqrt(sum(x * x for x in b)) or 1e-10
    sim = dot / (norm_a * norm_b)
    return sim if math.isfinite(sim) else 0.0


class DefaultVectorStoreAdapter(VectorStoreAdapter):
    """Simple in-memory vector store with JSON persistence."""

    def __init__(self) -> None:
        settings = get_settings()
        self._path = settings.vector_store_path
        self._path.mkdir(parents=True, exist_ok=True)
        self._store: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load from disk if exists."""
        f = self._path / "vectors.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                self._store = data.get("records", {})
            except (json.JSONDecodeError, OSError):
                self._store = {}

    def _save(self) -> None:
        """Persist to disk."""
        f = self._path / "vectors.json"
        f.write_text(json.dumps({"records": self._store}, indent=0))

    def _key(self, chunk_id: str, project_id: str, index_version: str) -> str:
        return f"{project_id}:{index_version}:{chunk_id}"

    def upsert(self, records: list[VectorRecord]) -> None:
        """Upsert records."""
        for r in records:
            if r.is_deleted:
                continue
            key = self._key(r.chunk_id, r.project_id, r.index_version)
            self._store[key] = {
                "chunk_id": r.chunk_id,
                "vector": r.vector,
                "project_id": r.project_id,
                "file_id": r.file_id,
                "parent_id": r.parent_id,
                "chunk_type": r.chunk_type,
                "chunk_text": r.chunk_text,
                "loc": r.loc,
                "index_version": r.index_version,
                "doc_hash": r.doc_hash,
            }
        self._save()

    def search(
        self,
        vector: list[float],
        top_k: int,
        project_id: str,
        index_version: str,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Search by cosine similarity."""
        prefix = f"{project_id}:{index_version}:"
        candidates: list[tuple[float, dict]] = []
        for key, rec in self._store.items():
            if not key.startswith(prefix):
                continue
            if filters:
                skip = False
                for fk, fv in filters.items():
                    if rec.get(fk) != fv:
                        skip = True
                        break
                if skip:
                    continue
            sim = _cosine_similarity(vector, rec["vector"])
            candidates.append((sim, rec))
        candidates.sort(key=lambda x: -x[0])
        return [
            SearchHit(
                chunk_id=r["chunk_id"],
                score=sim,
                project_id=r["project_id"],
                file_id=r["file_id"],
                parent_id=r["parent_id"],
                chunk_type=r["chunk_type"],
                chunk_text=r.get("chunk_text", ""),
                loc=r["loc"],
                index_version=r["index_version"],
                doc_hash=r["doc_hash"],
            )
            for sim, r in candidates[:top_k]
        ]

    def delete_by_file(
        self,
        project_id: str,
        file_id: str,
        index_version: str,
    ) -> None:
        """Delete all vectors for a file."""
        prefix = f"{project_id}:{index_version}:"
        to_delete = [
            k for k, r in self._store.items()
            if k.startswith(prefix) and r.get("file_id") == file_id
        ]
        for k in to_delete:
            del self._store[k]
        self._save()

    def switch_version(
        self,
        project_id: str,
        new_version: str,
    ) -> None:
        """No-op for simple store - version is in key."""
        pass
