"""Search service - recall + rerank."""

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.core.tracing import get_trace_id

logger = get_logger("app.services.retrieval.search")
from app.db.models import Chunk, Parent, Project
from app.db.session import get_db


@dataclass
class RecallHit:
    """Recall result hit."""

    chunk_id: str
    score: float
    chunk_text: str
    parent_id: str
    file_id: str
    chunk_type: str
    loc: dict[str, Any]


@dataclass
class RerankHit:
    """Rerank result hit."""

    chunk_id: str
    score: float
    chunk_text: str
    parent_id: str
    file_id: str
    chunk_type: str
    loc: dict[str, Any]


@dataclass
class SearchResult:
    """Full search result."""

    trace_id: str
    recall: list[RecallHit]
    rerank: list[RerankHit]
    timings_ms: dict[str, int]
    debug: dict[str, Any] = field(default_factory=dict)


def search(
    project_id: str,
    query: str,
    index_version: str | None = None,
    recall_top_k: int = 50,
    rerank_top_n: int = 10,
    filters: dict[str, Any] | None = None,
    debug: bool = False,
) -> SearchResult:
    """Execute recall + rerank search."""
    from app.services.providers.registry import (
        get_embedding_provider,
        get_rerank_provider,
        get_vector_store_adapter,
    )

    trace_id = get_trace_id()
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    # Resolve index version
    db = get_db()
    try:
        if not index_version:
            proj = db.query(Project).filter(Project.project_id == project_id).first()
            index_version = proj.active_index_version if proj else None
        if not index_version:
            logger.warning("No index version for project=%s", project_id)
            return SearchResult(
                trace_id=trace_id,
                recall=[],
                rerank=[],
                timings_ms={"embed": 0, "recall": 0, "rerank": 0},
                debug={"error": "No index version"} if debug else {},
            )
    finally:
        db.close()

    # Embed query
    embedder = get_embedding_provider()
    query_vec = embedder.embed([query])[0]
    timings["embed"] = (time.perf_counter() - t0) * 1000
    # #region agent log
    _bad = lambda v: isinstance(v, float) and not math.isfinite(v)
    _vec_bad = any(_bad(x) for x in query_vec) if query_vec else False
    _sample = [float(x) if math.isfinite(x) else "nan_or_inf" for x in (query_vec[:3] if query_vec else [])]
    from pathlib import Path
    _log_path = Path(__file__).resolve().parents[5] / ".cursor" / "debug.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    open(_log_path, "a").write(
        json.dumps({"hypothesisId": "H3", "location": "search.py:query_vec", "message": "embedding output", "data": {"vec_has_bad_float": _vec_bad, "vec_len": len(query_vec) if query_vec else 0, "sample": _sample}, "timestamp": time.time()}) + "\n"
    )
    # #endregion

    # Vector search
    t1 = time.perf_counter()
    vs = get_vector_store_adapter()
    hits = vs.search(
        vector=query_vec,
        top_k=recall_top_k,
        project_id=project_id,
        index_version=index_version,
        filters=filters,
    )
    def _safe_float(v: float) -> float:
        """Replace NaN/Inf with 0.0 for JSON compliance."""
        return v if isinstance(v, (int, float)) and math.isfinite(v) else 0.0

    recall = [
        RecallHit(
            chunk_id=h.chunk_id,
            score=_safe_float(h.score),
            chunk_text=h.chunk_text,
            parent_id=h.parent_id,
            file_id=h.file_id,
            chunk_type=h.chunk_type,
            loc=h.loc,
        )
        for h in hits
    ]
    timings["recall"] = (time.perf_counter() - t1) * 1000
    # #region agent log
    _recall_scores = [s if math.isfinite(s) else "nan_or_inf" for s in [r.score for r in recall[:5]]]
    _recall_bad = any(_bad(r.score) for r in recall[:5])
    _loc_bad = False
    for r in recall[:3]:
        for k, v in (r.loc or {}).items():
            if _bad(v):
                _loc_bad = True
                break
    from pathlib import Path
    _log_path = Path(__file__).resolve().parents[5] / ".cursor" / "debug.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    open(_log_path, "a").write(
        json.dumps({"hypothesisId": "H1,H4", "location": "search.py:recall", "message": "recall scores and loc", "data": {"recall_scores": _recall_scores, "recall_has_bad_float": _recall_bad, "loc_has_bad_float": _loc_bad}, "timestamp": time.time()}) + "\n"
    )
    # #endregion

    # Rerank
    t2 = time.perf_counter()
    if recall:
        rerank_provider = get_rerank_provider()
        candidates = [r.chunk_text for r in recall]
        reranked = rerank_provider.rerank(query, candidates, rerank_top_n)
        rerank = []
        for rr in reranked:
            orig = recall[rr.index]
            rerank.append(
                RerankHit(
                    chunk_id=orig.chunk_id,
                    score=_safe_float(rr.score),
                    chunk_text=orig.chunk_text,
                    parent_id=orig.parent_id,
                    file_id=orig.file_id,
                    chunk_type=orig.chunk_type,
                    loc=orig.loc,
                )
            )
    else:
        rerank = []
    timings["rerank"] = (time.perf_counter() - t2) * 1000
    # #region agent log
    _rerank_scores = [s if math.isfinite(s) else "nan_or_inf" for s in [r.score for r in rerank[:5]]]
    _rerank_bad = any(_bad(r.score) for r in rerank[:5])
    _timings_bad = any(_bad(v) for v in timings.values())
    _timings_safe = {k: (v if math.isfinite(v) else "nan_or_inf") for k, v in timings.items()}
    from pathlib import Path
    _log_path = Path(__file__).resolve().parents[5] / ".cursor" / "debug.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    open(_log_path, "a").write(
        json.dumps({"hypothesisId": "H2,H5", "location": "search.py:rerank_timings", "message": "rerank scores and timings", "data": {"rerank_scores": _rerank_scores, "rerank_has_bad_float": _rerank_bad, "timings": _timings_safe, "timings_has_bad": _timings_bad}, "timestamp": time.time()}) + "\n"
    )
    # #endregion

    timings_ms = {k: int(v) for k, v in timings.items()}
    # #region agent log
    def _scan_bad(obj, path=""):
        if isinstance(obj, float) and not math.isfinite(obj):
            return [path]
        if isinstance(obj, dict):
            out = []
            for k, v in obj.items():
                out.extend(_scan_bad(v, f"{path}.{k}"))
            return out
        if isinstance(obj, (list, tuple)):
            out = []
            for i, v in enumerate(obj):
                out.extend(_scan_bad(v, f"{path}[{i}]"))
            return out
        return []
    _to_return = {"recall": [{"score": r.score, "loc": r.loc} for r in recall], "rerank": [{"score": r.score, "loc": r.loc} for r in rerank], "timings_ms": timings_ms, "debug": {"index_version": index_version} if debug else {}}
    _bad_paths = _scan_bad(_to_return)
    from pathlib import Path
    _log_path = Path(__file__).resolve().parents[5] / ".cursor" / "debug.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    open(_log_path, "a").write(
        json.dumps({"hypothesisId": "H1-H5", "location": "search.py:pre_return", "message": "bad float paths in result", "data": {"bad_paths": _bad_paths}, "timestamp": time.time()}) + "\n"
    )
    # #endregion
    return SearchResult(
        trace_id=trace_id,
        recall=recall,
        rerank=rerank,
        timings_ms=timings_ms,
        debug={"index_version": index_version} if debug else {},
    )


def get_parent_with_children(
    project_id: str,
    parent_id: str,
) -> dict[str, Any] | None:
    """Get parent with its children for expand view."""
    db = get_db()
    try:
        parent = (
            db.query(Parent)
            .filter(
                Parent.project_id == project_id,
                Parent.parent_id == parent_id,
                Parent.is_deleted == False,
            )
            .first()
        )
        if not parent:
            return None
        chunks = (
            db.query(Chunk)
            .filter(
                Chunk.project_id == project_id,
                Chunk.parent_id == parent_id,
                Chunk.is_deleted == False,
            )
            .order_by(Chunk.seq_start)
            .all()
        )
        return {
            "parent_id": parent.parent_id,
            "parent_type": parent.parent_type,
            "loc": parent.loc,
            "parent_text": parent.parent_text,
            "children": [
                {
                    "chunk_id": c.chunk_id,
                    "chunk_type": c.chunk_type,
                    "chunk_text": c.chunk_text,
                    "seq_start": c.seq_start,
                    "seq_end": c.seq_end,
                }
                for c in chunks
            ],
        }
    finally:
        db.close()
