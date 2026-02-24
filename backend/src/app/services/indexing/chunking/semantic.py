"""Semantic chunking - split when adjacent similarity < threshold."""

import uuid
from typing import TYPE_CHECKING

from app.services.indexing.chunking.base import (
    ChildChunk,
    ChunkingPolicy,
    ParentNode,
    estimate_tokens,
)
from app.services.parsing.base import Loc, TableBlock, TextBlock

if TYPE_CHECKING:
    from app.services.providers import EmbeddingProvider


class SemanticChunkingPolicy(ChunkingPolicy):
    """Semantic chunking using paragraph-level embeddings."""

    policy_name = "semantic"
    policy_version = "1.0"

    def __init__(
        self,
        threshold: float = 0.72,
        hard_max_tokens: int = 380,
        embedding_provider: "EmbeddingProvider | None" = None,
    ):
        self.threshold = threshold
        self.hard_max_tokens = hard_max_tokens
        self._embedding_provider = embedding_provider

    def _get_embedder(self) -> "EmbeddingProvider":
        if self._embedding_provider is None:
            from app.services.providers.registry import get_embedding_provider
            return get_embedding_provider()
        return self._embedding_provider

    def build_parents(self, blocks: list, source_type: str) -> list[ParentNode]:
        """Use structure_fixed for parent building."""
        from app.services.indexing.chunking.structure_fixed import StructureFixedChunkingPolicy
        policy = StructureFixedChunkingPolicy()
        return policy.build_parents(blocks, source_type)

    def build_children(self, parent: ParentNode) -> list[ChildChunk]:
        """Split by semantic similarity between paragraphs."""
        paragraphs: list[str] = []
        for b in parent.blocks:
            if isinstance(b, TableBlock):
                paragraphs.append(b.content)
            elif isinstance(b, TextBlock):
                for p in b.content.split("\n\n"):
                    if p.strip():
                        paragraphs.append(p.strip())
        if not paragraphs:
            return []
        if len(paragraphs) == 1:
            text = paragraphs[0]
            if estimate_tokens(text) > self.hard_max_tokens:
                from app.services.indexing.chunking.structure_fixed import StructureFixedChunkingPolicy
                sf = StructureFixedChunkingPolicy(hard_max_tokens=self.hard_max_tokens)
                return sf.build_children(parent)
            return [
                ChildChunk(
                    chunk_id=str(uuid.uuid4()),
                    parent_id=parent.parent_id,
                    chunk_type="text",
                    chunk_text=text,
                    embedding_text=text,
                    seq_start=parent.seq_start,
                    seq_end=parent.seq_end,
                    loc=parent.loc.to_dict(),
                    chunk_policy=self.policy_name,
                    boundary_signals={"reason": "single_paragraph", "threshold": self.threshold},
                    policy_version=self.policy_version,
                )
            ]
        embedder = self._get_embedder()
        vectors = embedder.embed(paragraphs)
        chunks: list[list[str]] = []
        current = [paragraphs[0]]
        for i in range(1, len(paragraphs)):
            sim = self._cosine_sim(vectors[i - 1], vectors[i])
            if sim < self.threshold and current:
                chunks.append(current)
                current = [paragraphs[i]]
            else:
                current.append(paragraphs[i])
            total = sum(estimate_tokens(p) for p in current)
            if total > self.hard_max_tokens and current:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)
        result: list[ChildChunk] = []
        for group in chunks:
            text = "\n\n".join(group)
            if estimate_tokens(text) > self.hard_max_tokens:
                from app.services.indexing.chunking.structure_fixed import StructureFixedChunkingPolicy
                sf = StructureFixedChunkingPolicy(hard_max_tokens=self.hard_max_tokens)
                fake_parent = ParentNode(
                    parent_id=parent.parent_id,
                    parent_type=parent.parent_type,
                    loc=parent.loc,
                    parent_text=text,
                    seq_start=parent.seq_start,
                    seq_end=parent.seq_end,
                    blocks=[TextBlock(content=text, loc=parent.loc)],
                )
                result.extend(sf.build_children(fake_parent))
            else:
                result.append(
                    ChildChunk(
                        chunk_id=str(uuid.uuid4()),
                        parent_id=parent.parent_id,
                        chunk_type="text",
                        chunk_text=text,
                        embedding_text=text,
                        seq_start=parent.seq_start,
                        seq_end=parent.seq_end,
                        loc=parent.loc.to_dict(),
                        chunk_policy=self.policy_name,
                        boundary_signals={"reason": "semantic", "threshold": self.threshold},
                        policy_version=self.policy_version,
                    )
                )
        return result

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1e-10
        nb = math.sqrt(sum(x * x for x in b)) or 1e-10
        return dot / (na * nb)
