"""SQLAlchemy models for SQLite."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {
        dict[str, Any]: JSON,
    }


class Project(Base):
    """Project entity - root isolation unit."""

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    active_index_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class File(Base):
    """Uploaded file metadata."""

    __tablename__ = "files"

    file_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.project_id"), index=True
    )
    filename: Mapped[str] = mapped_column(String(512))
    doc_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(32))  # pdf, pptx, docx
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Parent(Base):
    """Parent nodes - display & citation containers (page, slide, section)."""

    __tablename__ = "parents"

    parent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.project_id"), index=True
    )
    file_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("files.file_id"), index=True
    )
    parent_type: Mapped[str] = mapped_column(String(32))  # page, slide, section
    loc: Mapped[dict] = mapped_column(JSON)  # page_num, slide_num, heading_path
    parent_text: Mapped[str] = mapped_column(Text)
    seq_start: Mapped[int] = mapped_column(Integer)
    seq_end: Mapped[int] = mapped_column(Integer)
    index_version: Mapped[str] = mapped_column(String(64), index=True)
    doc_hash: Mapped[str] = mapped_column(String(64), index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_parents_project_version", "project_id", "index_version"),
    )


class Chunk(Base):
    """Chunk metadata (vectors stored in VectorStoreAdapter)."""

    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.project_id"), index=True
    )
    file_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("files.file_id"), index=True
    )
    parent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("parents.parent_id"), index=True
    )
    chunk_type: Mapped[str] = mapped_column(String(32))  # text, table, image_ocr, image_caption
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding_text: Mapped[str] = mapped_column(Text)
    seq_start: Mapped[int] = mapped_column(Integer)
    seq_end: Mapped[int] = mapped_column(Integer)
    loc: Mapped[dict] = mapped_column(JSON)
    chunk_policy: Mapped[str] = mapped_column(String(64))
    boundary_signals: Mapped[dict] = mapped_column(JSON, nullable=True)
    policy_version: Mapped[str] = mapped_column(String(32))
    index_version: Mapped[str] = mapped_column(String(64), index=True)
    doc_hash: Mapped[str] = mapped_column(String(64), index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class Job(Base):
    """Async index build job."""

    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.project_id"), index=True
    )
    status: Mapped[str] = mapped_column(String(32))  # pending, running, completed, failed
    index_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class IngestionLog(Base):
    """Idempotency log - skip duplicate ingestion."""

    __tablename__ = "ingestion_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    file_id: Mapped[str] = mapped_column(String(64), index=True)
    doc_hash: Mapped[str] = mapped_column(String(64), index=True)
    index_version: Mapped[str] = mapped_column(String(64), index=True)

    __table_args__ = (
        Index(
            "ix_ingestion_log_project_hash_version",
            "project_id",
            "doc_hash",
            "index_version",
            unique=True,
        ),
    )
