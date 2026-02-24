"""Stub Embedding provider - deterministic fake embeddings."""

import hashlib
import math
import struct

from app.services.providers.base import EmbeddingProvider


def _safe_float(val: float) -> float:
    """Replace NaN/Inf with 0.0 for deterministic stub output."""
    return val if math.isfinite(val) else 0.0


class StubEmbeddingProvider(EmbeddingProvider):
    """Stub implementation - deterministic fake vectors from text hash."""

    DIMENSION = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic fake embeddings."""
        result = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            vec = []
            for i in range(0, min(len(h), self.DIMENSION * 4), 4):
                val = struct.unpack("f", h[i : i + 4])[0] if i + 4 <= len(h) else 0.0
                val = _safe_float(val)
                vec.append(val % 1.0 - 0.5)
            while len(vec) < self.DIMENSION:
                vec.append(0.0)
            result.append(vec[: self.DIMENSION])
        return result

    @property
    def dimension(self) -> int:
        return self.DIMENSION
