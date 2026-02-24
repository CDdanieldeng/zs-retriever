"""OpenAI Embedding API provider."""

import os
from typing import Any

import httpx

from app.services.providers.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding via OpenAI API (text-embedding-3-small, text-embedding-3-large)."""

    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSION = 1536  # text-embedding-3-small default
    API_URL = "https://api.openai.com/v1/embeddings"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
    ) -> None:
        """
        Args:
            api_key: OpenAI API key, default from OPENAI_API_KEY env
            base_url: Override API base URL (e.g. for proxy)
            model: Model name, default text-embedding-3-small
            dimension: Output dimension (supported by v3 models)
        """
        from app.config import get_settings

        settings = get_settings()
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._base_url = (
            base_url
            or getattr(settings, "embedding_openai_base_url", None)
            or self.API_URL.rsplit("/", 1)[0]
        )
        self._model = (
            model
            or getattr(settings, "embedding_openai_model", None)
            or self.DEFAULT_MODEL
        )
        self._dimension = (
            dimension
            or getattr(settings, "embedding_dimension", None)
            or self.DEFAULT_DIMENSION
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via OpenAI API."""
        if not texts:
            return []
        url = f"{self._base_url.rstrip('/')}/embeddings"
        payload: dict[str, Any] = {
            "model": self._model,
            "input": texts if len(texts) > 1 else texts[0],
            "encoding_format": "float",
        }
        if self._dimension:
            payload["dimensions"] = self._dimension
        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    @property
    def dimension(self) -> int:
        return self._dimension
