"""Stub Vision caption provider."""

from app.services.providers.base import VisionCaptionProvider, VisionOutput


class StubVisionCaptionProvider(VisionCaptionProvider):
    """Stub implementation - returns placeholder caption."""

    def caption(self, image_bytes: bytes) -> VisionOutput:
        """Return placeholder caption."""
        return VisionOutput(
            summary="[Stub: No vision caption]",
            bullets=[],
            entities=[],
            chart_readout=None,
        )
