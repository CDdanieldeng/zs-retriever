"""ChunkingPolicy interface and data types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.services.parsing.base import Block, Loc


def estimate_tokens(text: str) -> int:
    """Estimate token count (~4 chars per token)."""
    return max(1, len(text) // 4)


@dataclass
class ParentNode:
    """Parent node - display/citation container (page, slide, section)."""

    parent_id: str
    parent_type: str  # page, slide, section
    loc: Loc
    parent_text: str
    seq_start: int
    seq_end: int
    blocks: list[Block] = field(default_factory=list)


@dataclass
class ChildChunk:
    """Child chunk - retrieval unit."""

    chunk_id: str
    parent_id: str
    chunk_type: str  # text, table, image_ocr, image_caption
    chunk_text: str
    embedding_text: str
    seq_start: int
    seq_end: int
    loc: dict[str, Any]
    chunk_policy: str
    boundary_signals: dict[str, Any]
    policy_version: str


class ChunkingPolicy(ABC):
    """Chunking policy interface."""

    policy_name: str = "base"
    policy_version: str = "1.0"

    @abstractmethod
    def build_parents(self, blocks: list[Block], source_type: str) -> list[ParentNode]:
        """Build parent nodes from blocks."""
        ...

    @abstractmethod
    def build_children(self, parent: ParentNode) -> list[ChildChunk]:
        """Build child chunks from a parent."""
        ...
