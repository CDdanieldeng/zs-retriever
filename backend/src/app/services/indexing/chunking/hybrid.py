"""Hybrid chunking - structure first, semantic refinement if parent >= 600 tokens."""

from app.services.indexing.chunking.base import (
    ChildChunk,
    ChunkingPolicy,
    ParentNode,
    estimate_tokens,
)
from app.services.parsing.base import Block


class HybridChunkingPolicy(ChunkingPolicy):
    """Structure segmentation first; semantic refinement if parent large enough."""

    policy_name = "hybrid"
    policy_version = "1.0"

    def __init__(
        self,
        semantic_enabled_min_tokens: int = 600,
        semantic_threshold: float = 0.72,
    ):
        self.semantic_enabled_min_tokens = semantic_enabled_min_tokens
        self.semantic_threshold = semantic_threshold

    def build_parents(self, blocks: list[Block], source_type: str) -> list[ParentNode]:
        """Use structure_fixed for parent building."""
        from app.services.indexing.chunking.structure_fixed import StructureFixedChunkingPolicy
        policy = StructureFixedChunkingPolicy()
        return policy.build_parents(blocks, source_type)

    def build_children(self, parent: ParentNode) -> list[ChildChunk]:
        """Use semantic if parent >= min_tokens, else structure_fixed."""
        from app.services.indexing.chunking.semantic import SemanticChunkingPolicy
        from app.services.indexing.chunking.structure_fixed import StructureFixedChunkingPolicy

        token_count = estimate_tokens(parent.parent_text)
        if token_count >= self.semantic_enabled_min_tokens:
            policy = SemanticChunkingPolicy(threshold=self.semantic_threshold)
            return policy.build_children(parent)
        policy = StructureFixedChunkingPolicy()
        return policy.build_children(parent)
