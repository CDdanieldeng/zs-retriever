"""Central configuration for the Retriever Service."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="RETRIEVER_",
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore DASHSCOPE_API_KEY, OPENAI_API_KEY etc. (used via os.getenv in providers)
    )

    # Paths
    data_dir: Path = Field(default=Path("data"), description="Base data directory")
    sqlite_path: Path = Field(
        default=Path("data/retriever.db"),
        description="SQLite database path",
    )
    files_storage_path: Path = Field(
        default=Path("data/files"),
        description="Uploaded files storage path",
    )
    vector_store_path: Path = Field(
        default=Path("data/vectors"),
        description="Vector store persistence path",
    )

    # Image pipeline
    enable_ocr: bool = Field(default=False, description="Enable OCR for images")
    enable_vision_caption: bool = Field(
        default=False,
        description="Enable vision captioning for images",
    )

    # Chunking
    chunking_policy: Literal["structure_fixed", "semantic", "hybrid"] = Field(
        default="hybrid",
        description="Chunking policy: structure_fixed, semantic, or hybrid",
    )
    enable_semantic_chunking: bool = Field(
        default=False,
        description="Enable semantic chunking (expensive, off by default)",
    )
    semantic_threshold: float = Field(
        default=0.72,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for semantic split",
    )
    semantic_enabled_min_tokens: int = Field(
        default=600,
        ge=0,
        description="Min parent tokens to enable semantic refinement in hybrid",
    )

    # Structure-fixed chunking params
    target_tokens: int = Field(default=280, ge=1)
    overlap_tokens: int = Field(default=60, ge=0)
    hard_max_tokens: int = Field(default=380, ge=1)

    # Quick switch: "api" (Qwen API) or "local" (HF + CrossEncoder). Overrides embedding/rerank when set.
    provider_mode: Literal["api", "local"] | None = Field(
        default=None,
        description="Set to 'api' or 'local' to switch embedding+rerank at once. api=Qwen API, local=HF+CrossEncoder",
    )
    # Provider class names (dotted path)
    ocr_provider: str = Field(
        default="app.services.providers.ocr_stub.StubOcrProvider",
    )
    vision_caption_provider: str = Field(
        default="app.services.providers.vision_qwen_vl.QwenVisionCaptionProvider",
        description="Vision: QwenVisionCaptionProvider (qwen3-vl-flash, default), vision_stub",
    )
    # Qwen Vision API (DashScope)
    vision_qwen_api_model: str | None = Field(
        default=None,
        description="Qwen Vision API model: qwen3-vl-flash",
    )
    vision_qwen_api_base_url: str | None = Field(
        default=None,
        description="Qwen Vision API base URL",
    )
    embedding_provider: str = Field(
        default="app.services.providers.embedding_qwen_api.QwenEmbeddingProvider",
        description="Embedding: QwenEmbeddingProvider (API, default), OpenAIEmbeddingProvider, HuggingFaceQwenEmbeddingProvider, embedding_stub",
    )
    embedding_model_name: str | None = Field(
        default=None,
        description="HF model for local Qwen embedding",
    )
    embedding_dimension: int | None = Field(
        default=None,
        ge=32,
        le=3072,
        description="Embedding output dimension",
    )
    embedding_device: str | None = Field(
        default=None,
        description="Device for local embedding: cuda, mps, cpu",
    )
    # Qwen API (DashScope)
    embedding_qwen_api_model: str | None = Field(
        default=None,
        description="Qwen API model: text-embedding-v3, text-embedding-v4",
    )
    embedding_qwen_api_base_url: str | None = Field(
        default=None,
        description="Qwen embedding API base URL",
    )
    # OpenAI API
    embedding_openai_model: str | None = Field(
        default=None,
        description="OpenAI embedding model: text-embedding-3-small, text-embedding-3-large",
    )
    embedding_openai_base_url: str | None = Field(
        default=None,
        description="OpenAI embedding API base URL",
    )
    rerank_provider: str = Field(
        default="app.services.providers.rerank_qwen_api.QwenRerankProvider",
        description="Rerank: QwenRerankProvider (API, default), OpenAIRerankProvider, CrossEncoderRerankProvider, rerank_stub",
    )
    rerank_model_name: str | None = Field(
        default=None,
        description="HF model for local reranker, e.g. BAAI/bge-reranker-large",
    )
    rerank_device: str | None = Field(
        default=None,
        description="Device for local reranker: cuda, mps, cpu",
    )
    # Qwen Rerank API
    rerank_qwen_api_model: str | None = Field(
        default=None,
        description="Qwen rerank API model: qwen3-rerank, gte-rerank-v2",
    )
    rerank_qwen_api_base_url: str | None = Field(
        default=None,
        description="Qwen rerank API base URL",
    )
    # OpenAI Rerank (embedding-based)
    rerank_openai_model: str | None = Field(
        default=None,
        description="OpenAI embedding model for rerank: text-embedding-3-small",
    )
    rerank_openai_base_url: str | None = Field(
        default=None,
        description="OpenAI API base URL for rerank",
    )
    vector_store_adapter: str = Field(
        default="app.services.providers.vector_store_default.DefaultVectorStoreAdapter",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
