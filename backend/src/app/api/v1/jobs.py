"""Job status endpoint."""

from fastapi import APIRouter, HTTPException

from app.schemas.job import JobResponse
from app.services.indexing.job_runner import get_job_status

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    """Get job status and metrics."""
    data = get_job_status(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**data)
