"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load backend/.env into os.environ (pydantic-settings does not do this)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.api.router import api_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup, cleanup on shutdown."""
    init_db()
    yield


app = FastAPI(
    title="Retriever Service",
    description="Recall + Rerank only, no generation",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/v1")
