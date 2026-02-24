"""PDF parser using PyMuPDF (fitz)."""

from pathlib import Path
from typing import BinaryIO

import fitz  # PyMuPDF

from app.services.parsing.base import (
    Block,
    ImageBlock,
    Loc,
    SourceType,
    TableBlock,
    TextBlock,
)


class PdfParser:
    """Parse PDF files into blocks. Parent = page."""

    def parse(self, content: bytes | BinaryIO, filename: str = "") -> list[Block]:
        """Parse PDF content into blocks."""
        if isinstance(content, bytes):
            doc = fitz.open(stream=content, filetype="pdf")
        else:
            doc = fitz.open(stream=content.read(), filetype="pdf")
        blocks: list[Block] = []
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                loc = Loc(page_num=page_num + 1)

                # Text
                text = page.get_text()
                if text.strip():
                    blocks.append(TextBlock(content=text.strip(), loc=loc))

                # Images
                for img_index, img in enumerate(page.get_images()):
                    try:
                        xref = img[0]
                        base_img = doc.extract_image(xref)
                        img_bytes = base_img["image"]
                        blocks.append(
                            ImageBlock(
                                content=f"[Image page {page_num + 1}]",
                                loc=loc,
                                metadata={"image_index": img_index},
                                image_bytes=img_bytes,
                            )
                        )
                    except Exception:
                        pass

                # Simple table detection: look for tabular text patterns
                # PyMuPDF doesn't have built-in table detection; use text blocks
                # For MVP we treat tables as part of text. Could add pdfplumber later.
        finally:
            doc.close()
        return blocks
