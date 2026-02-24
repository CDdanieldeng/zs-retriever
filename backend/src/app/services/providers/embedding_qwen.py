"""Hugging Face Qwen3-Embedding-0.6B provider."""

from typing import Any

from app.services.providers.base import EmbeddingProvider


class HuggingFaceQwenEmbeddingProvider(EmbeddingProvider):
    """Local embedding using Qwen/Qwen3-Embedding-0.6B via sentence-transformers."""

    DEFAULT_MODEL = "Qwen/Qwen3-Embedding-0.6B"
    DEFAULT_DIMENSION = 1024

    def __init__(
        self,
        model_name: str | None = None,
        dimension: int | None = None,
        device: str | None = None,
    ) -> None:
        """
        Args:
            model_name: HF model id, default Qwen/Qwen3-Embedding-0.6B
            dimension: Output dimension 32-1024 (MRL), default 1024
            device: torch device, e.g. 'cuda', 'mps', 'cpu'
        """
        from app.config import get_settings

        settings = get_settings()
        self._model_name = (
            model_name
            or getattr(settings, "embedding_model_name", None)
            or self.DEFAULT_MODEL
        )
        self._dimension = (
            dimension
            or getattr(settings, "embedding_dimension", None)
            or self.DEFAULT_DIMENSION
        )
        self._device = device or getattr(settings, "embedding_device", None)
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazy load model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
            )
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via Qwen3-Embedding."""
        if not texts:
            return []
        model = self._get_model()
        # encode returns ndarray (n, dim)
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        # Qwen3-Embedding supports MRL: truncate to target dimension if needed
        dim = self._dimension
        result: list[list[float]] = []
        for i in range(len(texts)):
            vec = embeddings[i].tolist()
            if len(vec) > dim:
                vec = vec[:dim]
            elif len(vec) < dim:
                vec = vec + [0.0] * (dim - len(vec))
            result.append(vec)
        return result

    @property
    def dimension(self) -> int:
        return self._dimension
