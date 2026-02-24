"""Search request/response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request body."""

    query: str = Field(..., min_length=1)
    index_version: str | None = None
    recall_top_k: int = Field(default=50, ge=1, le=200)
    rerank_top_n: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)
    debug: bool = False


class RecallHitSchema(BaseModel):
    chunk_id: str
    score: float
    chunk_text: str
    parent_id: str
    file_id: str
    chunk_type: str
    loc: dict[str, Any]


class RerankHitSchema(BaseModel):
    chunk_id: str
    score: float
    chunk_text: str
    parent_id: str
    file_id: str
    chunk_type: str
    loc: dict[str, Any]


class SearchResponse(BaseModel):
    trace_id: str
    recall: list[RecallHitSchema]
    rerank: list[RerankHitSchema]
    timings_ms: dict[str, int]
    debug: dict[str, Any] = Field(default_factory=dict)
