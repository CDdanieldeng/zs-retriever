"""Index build endpoint."""

from fastapi import APIRouter

from app.schemas.job import IndexBuildRequest, IndexBuildResponse
from app.services.indexing.job_runner import start_index_job

router = APIRouter(prefix="/indexes", tags=["indexes"])


@router.post("/build", response_model=IndexBuildResponse)
def build_index(body: IndexBuildRequest):
    """Start async index build job. Returns job_id."""
    job_id = start_index_job(
        project_id=body.project_id,
        file_ids=body.file_ids,
        index_version=body.index_version,
    )
    return IndexBuildResponse(job_id=job_id)
