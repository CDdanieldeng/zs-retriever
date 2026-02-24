"""BGE Reranker provider - CrossEncoder with BAAI/bge-reranker-large."""

from typing import Any

from app.services.providers.base import RerankProvider, RerankResult


class CrossEncoderRerankProvider(RerankProvider):
    """Rerank using BAAI/bge-reranker-large via sentence-transformers CrossEncoder."""

    DEFAULT_MODEL = "BAAI/bge-reranker-large"

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        """
        Args:
            model_name: HF model id, default BAAI/bge-reranker-large
            device: torch device, e.g. 'cuda', 'mps', 'cpu'
        """
        from app.config import get_settings

        settings = get_settings()
        self._model_name = (
            model_name
            or getattr(settings, "rerank_model_name", None)
            or self.DEFAULT_MODEL
        )
        self._device = device or getattr(settings, "rerank_device", None)
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazy load model."""
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self._model_name,
                device=self._device,
            )
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        """Rerank candidates by relevance to query using CrossEncoder."""
        if not candidates:
            return []
        model = self._get_model()
        ranked = model.rank(
            query,
            candidates,
            top_k=top_n,
            return_documents=False,
        )
        return [
            RerankResult(
                index=int(r["corpus_id"]),
                score=float(r["score"]),
                text=candidates[r["corpus_id"]],
            )
            for r in ranked
        ]
