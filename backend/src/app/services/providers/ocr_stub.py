"""Stub OCR provider - returns empty string."""

from app.services.providers.base import OcrProvider


class StubOcrProvider(OcrProvider):
    """Stub implementation - no actual OCR."""

    def extract_text(self, image_bytes: bytes) -> str:
        """Return empty string."""
        return ""
