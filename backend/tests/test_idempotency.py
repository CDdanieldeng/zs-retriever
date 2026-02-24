"""Tests for idempotent ingestion."""

import pytest

from app.services.ingestion.orchestrator import ingest_file


def test_idempotency_skip_duplicate(sample_pdf_bytes):
    """Duplicate file (same doc_hash) should be skipped."""
    project_id = "test_project_idemp"
    index_version = "v1"

    r1 = ingest_file(
        project_id=project_id,
        file_bytes=sample_pdf_bytes,
        filename="test.pdf",
        source_type="pdf",
        index_version=index_version,
    )
    assert not r1.skipped
    assert r1.error is None

    r2 = ingest_file(
        project_id=project_id,
        file_bytes=sample_pdf_bytes,
        filename="test.pdf",
        source_type="pdf",
        index_version=index_version,
        file_id=r1.file_id,
    )
    assert r2.skipped
