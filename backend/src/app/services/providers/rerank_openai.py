"""OpenAI embedding-based rerank provider.

OpenAI has no dedicated rerank API. This provider uses the embedding API
to re-score candidates by query-document similarity (cosine).
"""

import math
import os
from typing import Any

import httpx

from app.services.providers.base import RerankProvider, RerankResult


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1e-10
    norm_b = math.sqrt(sum(x * x for x in b)) or 1e-10
    sim = dot / (norm_a * norm_b)
    return sim if math.isfinite(sim) else 0.0


class OpenAIRerankProvider(RerankProvider):
    """Rerank via OpenAI embedding API - re-scores by query-doc similarity."""

    DEFAULT_MODEL = "text-embedding-3-small"
    API_URL = "https://api.openai.com/v1/embeddings"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Args:
            api_key: OpenAI API key, default from OPENAI_API_KEY env
            base_url: Override API base URL
            model: Embedding model for re-scoring
        """
        from app.config import get_settings

        settings = get_settings()
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._base_url = (
            base_url
            or getattr(settings, "rerank_openai_base_url", None)
            or self.API_URL.rsplit("/", 1)[0]
        )
        self._model = (
            model
            or getattr(settings, "rerank_openai_model", None)
            or self.DEFAULT_MODEL
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embedding API."""
        if not texts:
            return []
        url = f"{self._base_url.rstrip('/')}/embeddings"
        payload: dict[str, Any] = {
            "model": self._model,
            "input": texts,
            "encoding_format": "float",
        }
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

    def rerank(
        self,
        query: str,
        candidates: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        """Rerank by embedding similarity (query vs each candidate)."""
        if not candidates:
            return []
        query_vecs = self._embed([query])
        doc_vecs = self._embed(candidates)
        if not query_vecs or not doc_vecs:
            return []
        q = query_vecs[0]
        scored: list[tuple[int, float, str]] = [
            (i, _cosine_similarity(q, d), candidates[i])
            for i, d in enumerate(doc_vecs)
        ]
        scored.sort(key=lambda x: -x[1])
        return [
            RerankResult(index=idx, score=float(s), text=t)
            for idx, s, t in scored[:top_n]
        ]
