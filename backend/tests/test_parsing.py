"""Tests for parsing - PDF, DOCX."""

import pytest

from app.services.parsing.base import ImageBlock, TextBlock
from app.services.parsing.pdf_parser import PdfParser
from app.services.parsing.docx_parser import DocxParser


def test_pdf_parser(sample_pdf_bytes):
    parser = PdfParser()
    blocks = parser.parse(sample_pdf_bytes)
    assert len(blocks) >= 1
    text_blocks = [b for b in blocks if isinstance(b, TextBlock)]
    assert any("Hello" in b.content or "World" in b.content for b in text_blocks)


def test_docx_parser(sample_docx_bytes):
    parser = DocxParser()
    blocks = parser.parse(sample_docx_bytes)
    assert len(blocks) >= 1
    texts = [b.content for b in blocks if isinstance(b, TextBlock)]
    assert any("Test paragraph" in t for t in texts)
