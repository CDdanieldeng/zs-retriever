"""FastAPI application entry point."""

import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Load backend/.env into os.environ (pydantic-settings does not do this)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.api.router import api_router
from app.config import get_settings
from app.core.exceptions import NotFoundError, RetrieverError, ValidationError
from app.core.logging import get_logger, setup_logging
from app.core.tracing import get_trace_id, set_trace_id
from app.db.session import init_db

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup, cleanup on shutdown."""
    settings = get_settings()
    setup_logging(
        level=settings.log_level,
        format_type=settings.log_format,
        log_file=str(settings.log_file_path) if settings.log_file_path else None,
    )
    logger.info("Starting Retriever Service")
    init_db()
    yield
    logger.info("Shutting down Retriever Service")


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Set trace_id from X-Trace-Id header or generate one."""

    async def dispatch(self, request: Request, call_next):
        tid = request.headers.get("X-Trace-Id") or None
        set_trace_id(tid)
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log incoming requests and responses with status and duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "?"
        logger.info("Request %s %s from %s", method, path, client)
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            status = response.status_code
            logger.info(
                "Response %s %s -> %d (%.0fms)",
                method,
                path,
                status,
                duration_ms,
            )
            if status >= 400:
                logger.warning("Request failed: %s %s -> %d", method, path, status)
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "Request error %s %s after %.0fms: %s",
                method,
                path,
                duration_ms,
                exc,
            )
            raise


def exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions and return 500 with error details."""
    from fastapi.responses import JSONResponse

    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "trace_id": get_trace_id(),
        },
    )


app = FastAPI(
    title="Retriever Service",
    description="Recall + Rerank only, no generation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TraceIdMiddleware)  # Must run first to set trace_id for logs
app.add_exception_handler(Exception, exception_handler)

# RetrieverError -> 4xx with detail
@app.exception_handler(RetrieverError)
def retriever_error_handler(request: Request, exc: RetrieverError):
    from fastapi.responses import JSONResponse

    logger.warning("RetrieverError: %s", exc.message, extra={"details": exc.details})
    status = 400
    if isinstance(exc, NotFoundError):
        status = 404
    elif isinstance(exc, ValidationError):
        status = 422
    return JSONResponse(
        status_code=status,
        content={"detail": exc.message, "trace_id": get_trace_id(), **(exc.details or {})},
    )

app.include_router(api_router, prefix="/v1")
