"""Job schemas."""

from pydantic import BaseModel


class IndexBuildRequest(BaseModel):
    """Index build request body."""

    project_id: str
    file_ids: list[str] | None = None
    index_version: str | None = None


class IndexBuildResponse(BaseModel):
    job_id: str


class JobResponse(BaseModel):
    job_id: str
    project_id: str
    status: str
    index_version: str | None
    metrics: dict | None
    error_message: str | None
    created_at: str | None
    updated_at: str | None
