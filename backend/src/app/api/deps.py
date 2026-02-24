"""API dependencies."""

from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db


def get_project_id(
    project_id: Annotated[str, Path(description="Project ID")],
) -> str:
    """Validate and return project_id from path."""
    if not project_id or not project_id.strip():
        raise ValueError("project_id is required")
    return project_id.strip()


ProjectIdDep = Annotated[str, Depends(get_project_id)]
DbSessionDep = Annotated[Session, Depends(get_db)]
