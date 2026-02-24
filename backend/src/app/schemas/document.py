"""Document/upload schemas."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    project_id: str
