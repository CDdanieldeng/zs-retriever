"""Async index build job runner."""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.db.models import File, Job

logger = get_logger("app.services.indexing.job_runner")
from app.db.session import get_db
from app.services.ingestion.orchestrator import ingest_file

_executor = ThreadPoolExecutor(max_workers=2)
_job_status: dict[str, str] = {}


def _run_index_job(job_id: str, project_id: str, file_ids: list[str] | None, index_version: str) -> None:
    """Background job: index files for project."""
    db = get_db()
    try:
        db.query(Job).filter(Job.job_id == job_id).update(
            {"status": "running", "metrics": {"started_at": time.time()}}
        )
        db.commit()
    except Exception as e:
        logger.exception("Failed to update job %s to running: %s", job_id, e)
        db.rollback()
        db.close()
        return

    settings = get_settings()
    files_dir = settings.files_storage_path
    files_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Starting index job %s for project %s (version=%s, file_ids=%s)",
        job_id,
        project_id,
        index_version,
        file_ids,
    )
    metrics = {"files_processed": 0, "chunks_created": 0, "skipped_duplicates": 0}
    start = time.time()

    try:
        if file_ids:
            files = db.query(File).filter(
                File.project_id == project_id,
                File.file_id.in_(file_ids),
            ).all()
        else:
            files = db.query(File).filter(File.project_id == project_id).all()

        for f in files:
            path = files_dir / f.file_id
            if not path.exists():
                logger.warning("File not found on disk for job %s: %s (%s)", job_id, f.file_id, f.filename)
                continue
            with open(path, "rb") as fp:
                content = fp.read()
            result = ingest_file(
                project_id=project_id,
                file_bytes=content,
                filename=f.filename,
                source_type=f.source_type,
                index_version=index_version,
                file_id=f.file_id,
            )
            if result.skipped:
                metrics["skipped_duplicates"] += 1
            else:
                metrics["files_processed"] += 1
                metrics["chunks_created"] += result.chunks_created
            if result.error:
                logger.error(
                    "Ingestion failed for job %s file %s: %s",
                    job_id,
                    f.file_id,
                    result.error,
                )
                db.query(Job).filter(Job.job_id == job_id).update(
                    {"status": "failed", "error_message": result.error}
                )
                db.commit()
                return

        metrics["duration_ms"] = int((time.time() - start) * 1000)
        logger.info(
            "Index job %s completed: %d files, %d chunks in %dms",
            job_id,
            metrics["files_processed"],
            metrics["chunks_created"],
            metrics["duration_ms"],
        )
        db.query(Job).filter(Job.job_id == job_id).update(
            {"status": "completed", "metrics": metrics}
        )
        # Update project active version
        from app.db.models import Project
        db.query(Project).filter(Project.project_id == project_id).update(
            {"active_index_version": index_version}
        )
        db.commit()
    except Exception as e:
        logger.exception("Index job %s failed: %s", job_id, e)
        db.query(Job).filter(Job.job_id == job_id).update(
            {"status": "failed", "error_message": str(e)}
        )
        db.commit()
    finally:
        db.close()


def get_settings():
    from app.config import get_settings
    return get_settings()


def start_index_job(
    project_id: str,
    file_ids: list[str] | None = None,
    index_version: str | None = None,
) -> str:
    """Create job and enqueue. Returns job_id."""
    index_version = index_version or f"v{int(time.time())}"
    job_id = str(uuid.uuid4())
    db = get_db()
    try:
        db.add(
            Job(
                job_id=job_id,
                project_id=project_id,
                status="pending",
                index_version=index_version,
            )
        )
        db.commit()
        _executor.submit(_run_index_job, job_id, project_id, file_ids, index_version)
        return job_id
    finally:
        db.close()


def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Get job status and metrics."""
    db = get_db()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "project_id": job.project_id,
            "status": job.status,
            "index_version": job.index_version,
            "metrics": job.metrics,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }
    finally:
        db.close()
