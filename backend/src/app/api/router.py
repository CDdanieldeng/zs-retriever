"""Main API router."""

from fastapi import APIRouter

from app.api.v1 import indexes, jobs, projects

api_router = APIRouter()

api_router.include_router(projects.router)
api_router.include_router(indexes.router)
api_router.include_router(jobs.router)
