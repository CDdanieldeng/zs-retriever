"""Centralized logging for Retriever Service."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.tracing import get_trace_id


class TraceIdFilter(logging.Filter):
    """Inject trace_id into log records for request correlation."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Format logs as JSON for log aggregators (e.g. ELK, Datadog)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Include extra fields from record
        skip = {"name", "msg", "args", "created", "filename", "funcName", "levelname", "levelno", "lineno", "module", "msecs", "pathname", "process", "processName", "relativeCreated", "stack_info", "exc_info", "exc_text", "thread", "threadName", "message", "taskName", "trace_id"}
        for k, v in record.__dict__.items():
            if k not in skip and v is not None:
                try:
                    json.dumps(v)
                    payload[k] = v
                except (TypeError, ValueError):
                    payload[k] = str(v)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    *,
    level: str = "INFO",
    format_type: str = "text",
    log_file: str | None = None,
) -> None:
    """
    Configure application logging. Call once at startup.

    Args:
        level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        format_type: "text" (human-readable) or "json"
        log_file: Optional path to write logs to file
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates (e.g. in --reload)
    for h in root.handlers[:]:
        root.removeHandler(h)

    trace_filter = TraceIdFilter()

    if format_type == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(trace_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler (stderr)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.addFilter(trace_filter)
    root.addHandler(console)

    # File handler (optional)
    if log_file:
        try:
            from pathlib import Path
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(formatter)
            fh.addFilter(trace_filter)
            root.addHandler(fh)
        except OSError as e:
            root.warning("Could not create log file %s: %s", log_file, e)

    # Reduce noise from third-party libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # We log requests ourselves


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name. Prefer app.* namespace."""
    return logging.getLogger(name)
