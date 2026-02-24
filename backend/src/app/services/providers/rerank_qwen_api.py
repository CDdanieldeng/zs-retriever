"""Qwen/DashScope Rerank API provider."""

import math
import os
from typing import Any

import httpx

from app.services.providers.base import RerankProvider, RerankResult


class QwenRerankProvider(RerankProvider):
    """Rerank via DashScope/Qwen API (qwen3-rerank)."""

    DEFAULT_MODEL = "qwen3-rerank"
    API_URL = "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Args:
            api_key: DashScope API key, default from DASHSCOPE_API_KEY env
            base_url: Override API base URL
            model: Model name, default qwen3-rerank
        """
        from app.config import get_settings

        settings = get_settings()
        self._api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self._base_url = (
            base_url
            or getattr(settings, "rerank_qwen_api_base_url", None)
            or self.API_URL.rsplit("/", 1)[0]
        )
        self._model = (
            model
            or getattr(settings, "rerank_qwen_api_model", None)
            or self.DEFAULT_MODEL
        )

    def rerank(
        self,
        query: str,
        candidates: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        """Rerank candidates via Qwen/DashScope API."""
        if not candidates:
            return []
        url = f"{self._base_url.rstrip('/')}/reranks"
        payload: dict[str, Any] = {
            "model": self._model,
            "query": query,
            "documents": candidates,
            "top_n": top_n,
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
        # Compatible API returns results at top level; native API wraps in output
        results = data.get("results") or data.get("output", {}).get("results", [])
        out: list[RerankResult] = []
        for r in results:
            idx = int(r["index"])
            score = float(r.get("relevance_score", 0.0))
            if not math.isfinite(score):
                score = 0.0
            text = candidates[idx] if 0 <= idx < len(candidates) else ""
            out.append(RerankResult(index=idx, score=score, text=text))
        return out
