"""Provider interfaces - all external services go through these."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class VisionOutput:
    """Vision caption output schema (Qwen2.5-VL compatible)."""

    summary: str
    bullets: list[str]
    entities: list[str]
    chart_readout: str | None = None


@dataclass
class RerankResult:
    """Single rerank result with score and index."""

    index: int
    score: float
    text: str


@dataclass
class VectorRecord:
    """Record for vector store upsert/search."""

    chunk_id: str
    vector: list[float]
    project_id: str
    file_id: str
    parent_id: str
    chunk_type: str
    chunk_text: str
    loc: dict[str, Any]
    index_version: str
    doc_hash: str
    is_deleted: bool = False


@dataclass
class SearchHit:
    """Search result hit with metadata."""

    chunk_id: str
    score: float
    project_id: str
    file_id: str
    parent_id: str
    chunk_type: str
    chunk_text: str
    loc: dict[str, Any]
    index_version: str
    doc_hash: str


class OcrProvider(ABC):
    """OCR provider interface - extract text from images."""

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image bytes."""
        ...


class VisionCaptionProvider(ABC):
    """Vision caption provider (Qwen2.5-VL compatible)."""

    @abstractmethod
    def caption(self, image_bytes: bytes) -> VisionOutput:
        """Generate caption for image."""
        ...


class EmbeddingProvider(ABC):
    """Embedding provider - batch embed texts."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts, return list of vectors."""
        ...

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return 384  # Default for common models


class RerankProvider(ABC):
    """Rerank provider - score and reorder candidates."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        """Rerank candidates by relevance to query. Returns top_n in order."""
        ...


class VectorStoreAdapter(ABC):
    """Vector store adapter - pluggable ANN store."""

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        """Upsert records into vector store."""
        ...

    @abstractmethod
    def search(
        self,
        vector: list[float],
        top_k: int,
        project_id: str,
        index_version: str,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Search for similar vectors. Filter by project_id and index_version."""
        ...

    @abstractmethod
    def delete_by_file(
        self,
        project_id: str,
        file_id: str,
        index_version: str,
    ) -> None:
        """Delete all vectors for a file."""
        ...

    @abstractmethod
    def switch_version(
        self,
        project_id: str,
        new_version: str,
    ) -> None:
        """Switch active index version for project (if supported)."""
        ...
