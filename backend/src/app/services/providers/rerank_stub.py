"""Stub Rerank provider - returns candidates in original order with fake scores."""

from app.services.providers.base import RerankProvider, RerankResult


class StubRerankProvider(RerankProvider):
    """Stub implementation - pass-through with fake scores."""

    def rerank(
        self,
        query: str,
        candidates: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        """Return first top_n candidates with descending fake scores."""
        limited = candidates[:top_n]
        return [
            RerankResult(index=i, score=1.0 - (i * 0.01), text=c)
            for i, c in enumerate(limited)
        ]
