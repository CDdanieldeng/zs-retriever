"""Block types and source types for parsing."""

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    """Supported document source types."""

    PDF = "pdf"
    PPTX = "pptx"
    DOCX = "docx"


@dataclass
class Loc:
    """Location within document - page, slide, or section path."""

    page_num: int | None = None
    slide_num: int | None = None
    heading_path: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.page_num is not None:
            d["page_num"] = self.page_num
        if self.slide_num is not None:
            d["slide_num"] = self.slide_num
        if self.heading_path is not None:
            d["heading_path"] = self.heading_path
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Loc":
        return cls(
            page_num=d.get("page_num"),
            slide_num=d.get("slide_num"),
            heading_path=d.get("heading_path"),
        )


@dataclass
class Block(ABC):
    """Base block - content with location."""

    content: str
    loc: Loc
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TextBlock(Block):
    """Text content block."""

    pass


@dataclass
class TableBlock(Block):
    """Table content - stored as text representation."""

    pass


@dataclass
class ImageBlock(Block):
    """Image block - bytes for OCR/vision pipeline."""

    image_bytes: bytes = b""
