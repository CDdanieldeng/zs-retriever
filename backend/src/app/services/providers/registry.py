"""Provider registry - load providers from config."""

import importlib
from typing import Any

from app.config import get_settings


def _load_class(dotted_path: str) -> type:
    """Load class from dotted path like 'app.services.providers.ocr_stub.StubOcrProvider'."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def get_ocr_provider() -> Any:
    """Get configured OCR provider."""
    settings = get_settings()
    cls = _load_class(settings.ocr_provider)
    return cls()


def get_vision_caption_provider() -> Any:
    """Get configured Vision caption provider."""
    settings = get_settings()
    cls = _load_class(settings.vision_caption_provider)
    return cls()


# Presets for provider_mode
_EMBEDDING_BY_MODE = {
    "api": "app.services.providers.embedding_qwen_api.QwenEmbeddingProvider",
    "local": "app.services.providers.embedding_qwen.HuggingFaceQwenEmbeddingProvider",
}
_RERANK_BY_MODE = {
    "api": "app.services.providers.rerank_qwen_api.QwenRerankProvider",
    "local": "app.services.providers.rerank_cross_encoder.CrossEncoderRerankProvider",
}


def get_embedding_provider() -> Any:
    """Get configured Embedding provider."""
    settings = get_settings()
    path = (
        _EMBEDDING_BY_MODE.get(settings.provider_mode or "")
        or settings.embedding_provider
    )
    cls = _load_class(path)
    return cls()


def get_rerank_provider() -> Any:
    """Get configured Rerank provider."""
    settings = get_settings()
    path = (
        _RERANK_BY_MODE.get(settings.provider_mode or "")
        or settings.rerank_provider
    )
    cls = _load_class(path)
    return cls()


def get_vector_store_adapter() -> Any:
    """Get configured VectorStore adapter."""
    settings = get_settings()
    cls = _load_class(settings.vector_store_adapter)
    return cls()
