"""Tests for chunking policies."""

import pytest

from app.services.indexing.chunking.base import (
    ChildChunk,
    estimate_tokens,
    ParentNode,
)
from app.services.indexing.chunking.structure_fixed import StructureFixedChunkingPolicy
from app.services.parsing.base import Loc, TextBlock


def test_estimate_tokens():
    assert estimate_tokens("hello") >= 1
    assert estimate_tokens("a" * 40) >= 10


def test_structure_fixed_build_parents():
    policy = StructureFixedChunkingPolicy()
    blocks = [
        TextBlock(content="First paragraph.", loc=Loc(page_num=1)),
        TextBlock(content="Second paragraph.", loc=Loc(page_num=1)),
    ]
    parents = policy.build_parents(blocks, "pdf")
    assert len(parents) == 1
    assert parents[0].parent_type == "page"
    assert "First" in parents[0].parent_text


def test_structure_fixed_build_children():
    policy = StructureFixedChunkingPolicy(target_tokens=50, overlap_tokens=10)
    parent = ParentNode(
        parent_id="p1",
        parent_type="page",
        loc=Loc(page_num=1),
        parent_text=" ".join(["Sentence one."] * 20),
        seq_start=0,
        seq_end=0,
        blocks=[TextBlock(content="Sentence one. " * 20, loc=Loc(page_num=1))],
    )
    children = policy.build_children(parent)
    assert len(children) >= 1
    assert all(isinstance(c, ChildChunk) for c in children)
    assert all(c.chunk_policy == "structure_fixed" for c in children)
