"""Request tracing with trace_id."""

import uuid
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """Get current request trace_id, or generate one if not set."""
    tid = trace_id_var.get()
    if not tid:
        tid = str(uuid.uuid4())
        trace_id_var.set(tid)
    return tid


def set_trace_id(trace_id: str | None = None) -> str:
    """Set trace_id for current context. Returns the trace_id."""
    tid = trace_id or str(uuid.uuid4())
    trace_id_var.set(tid)
    return tid
