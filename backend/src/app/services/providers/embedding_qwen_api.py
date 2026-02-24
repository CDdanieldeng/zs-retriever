"""Qwen/DashScope Embedding API provider."""

import os
from typing import Any

import httpx

from app.services.providers.base import EmbeddingProvider


class QwenEmbeddingProvider(EmbeddingProvider):
    """Embedding via DashScope/Qwen API (text-embedding-v3, text-embedding-v4)."""

    DEFAULT_MODEL = "text-embedding-v4"
    DEFAULT_DIMENSION = 1024
    API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MAX_BATCH_SIZE = 10  # DashScope limit per request

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
    ) -> None:
        """
        Args:
            api_key: DashScope API key, default from DASHSCOPE_API_KEY env
            base_url: Override API base URL (e.g. Singapore: dashscope-intl.aliyuncs.com)
            model: Model name, default text-embedding-v3
            dimension: Output dimension (1024, 768, 512 for v3)
        """
        from app.config import get_settings

        settings = get_settings()
        self._api_key = (api_key or os.getenv("DASHSCOPE_API_KEY", "") or "").strip()
        self._base_url = (
            base_url
            or getattr(settings, "embedding_qwen_api_base_url", None)
            or self.API_URL
        )
        self._model = (
            model
            or getattr(settings, "embedding_qwen_api_model", None)
            or self.DEFAULT_MODEL
        )
        self._dimension = (
            dimension
            or getattr(settings, "embedding_dimension", None)
            or self.DEFAULT_DIMENSION
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via Qwen/DashScope API. Batches by 10 (API limit)."""
        if not texts:
            return []
        if not self._api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY is not set. Add it to backend/.env or set the env var."
            )
        url = f"{self._base_url.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i : i + self.MAX_BATCH_SIZE]
            payload: dict[str, Any] = {
                "model": self._model,
                "input": batch if len(batch) > 1 else batch[0],
                "encoding_format": "float",
                "dimensions": self._dimension,
            }
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            items = sorted(data["data"], key=lambda x: x["index"])
            all_embeddings.extend(item["embedding"] for item in items)
        return all_embeddings

    @property
    def dimension(self) -> int:
        return self._dimension
