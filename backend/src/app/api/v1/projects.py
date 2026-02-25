"""Project-scoped endpoints: upload, search, parents."""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.core.logging import get_logger
from app.core.tracing import set_trace_id
from app.db.models import File as FileModel, Project
from app.db.session import get_db
from app.schemas.document import UploadResponse
from app.schemas.search import (
    RecallHitSchema,
    RerankHitSchema,
    SearchRequest,
    SearchResponse,
)
from app.services.retrieval.search import get_parent_with_children, search

router = APIRouter(prefix="/projects", tags=["projects"])
logger = get_logger("app.api.v1.projects")


@router.post("/{project_id}/files/upload", response_model=UploadResponse)
def upload_file(
    project_id: str,
    file: UploadFile = File(...),
):
    """Upload file and optionally trigger immediate ingestion."""
    set_trace_id()
    logger.info("Upload request: project=%s filename=%s", project_id, file.filename)
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    ext = Path(file.filename).suffix.lower()
    source_type = None
    if ext == ".pdf":
        source_type = "pdf"
    elif ext == ".pptx":
        source_type = "pptx"
    elif ext == ".docx":
        source_type = "docx"
    if not source_type:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Use pdf, pptx, or docx.",
        )
    content = file.file.read()
    file_id = str(uuid.uuid4())
    settings = get_settings()
    files_dir = settings.files_storage_path
    files_dir.mkdir(parents=True, exist_ok=True)
    path = files_dir / file_id
    path.write_bytes(content)
    db = get_db()
    try:
        proj = db.query(Project).filter(Project.project_id == project_id).first()
        if not proj:
            db.add(Project(project_id=project_id))
        import hashlib
        doc_hash = hashlib.sha256(content).hexdigest()
        db.add(
            FileModel(
                file_id=file_id,
                project_id=project_id,
                filename=file.filename,
                doc_hash=doc_hash,
                source_type=source_type,
            )
        )
        db.commit()
    finally:
        db.close()
    logger.info("Uploaded file_id=%s for project=%s", file_id, project_id)
    return UploadResponse(file_id=file_id, filename=file.filename, project_id=project_id)


@router.post("/{project_id}/search", response_model=SearchResponse)
def search_endpoint(
    project_id: str,
    body: SearchRequest,
):
    """Recall + Rerank search."""
    set_trace_id()
    logger.info("Search: project=%s query=%s", project_id, (body.query[:50] + "..." if len(body.query) > 50 else body.query))
    try:
        result = search(
            project_id=project_id,
            query=body.query,
            index_version=body.index_version,
            recall_top_k=body.recall_top_k,
            rerank_top_n=body.rerank_top_n,
            filters=body.filters,
            debug=body.debug,
        )
    except Exception as e:
        logger.exception("Search failed for project=%s: %s", project_id, e)
        raise
    resp = SearchResponse(
        trace_id=result.trace_id,
        recall=[RecallHitSchema(**r.__dict__) for r in result.recall],
        rerank=[RerankHitSchema(**r.__dict__) for r in result.rerank],
        timings_ms=result.timings_ms,
        debug=result.debug,
    )
    # #region agent log
    import json
    import math
    from pathlib import Path
    def _scan_bad(obj, path=""):
        if isinstance(obj, float) and not math.isfinite(obj):
            return [path]
        if isinstance(obj, dict):
            return [p for k, v in obj.items() for p in _scan_bad(v, f"{path}.{k}")]
        if isinstance(obj, (list, tuple)):
            return [p for i, v in enumerate(obj) for p in _scan_bad(v, f"{path}[{i}]")]
        return []
    _d = resp.model_dump()
    _bad = _scan_bad(_d)
    _log = Path(__file__).resolve().parents[5] / ".cursor" / "debug.log"
    _log.parent.mkdir(parents=True, exist_ok=True)
    try:
        json.dumps(_d)
        _json_ok = True
    except (ValueError, TypeError) as e:
        _json_ok = False
        open(_log, "a").write(json.dumps({"hypothesisId": "H6", "location": "projects.py:search_endpoint", "message": "json.dumps failed", "data": {"error": str(e), "bad_paths": _bad}, "timestamp": __import__("time").time()}) + "\n")
    if _bad:
        open(_log, "a").write(json.dumps({"hypothesisId": "H6", "location": "projects.py:search_endpoint", "message": "bad floats in response", "data": {"bad_paths": _bad, "json_ok": _json_ok}, "timestamp": __import__("time").time()}) + "\n")
    # #endregion
    return resp


@router.get("/{project_id}/parents/{parent_id}")
def get_parent(
    project_id: str,
    parent_id: str,
):
    """Get parent with children for expand view."""
    set_trace_id()
    data = get_parent_with_children(project_id=project_id, parent_id=parent_id)
    if not data:
        raise HTTPException(status_code=404, detail="Parent not found")
    return data
