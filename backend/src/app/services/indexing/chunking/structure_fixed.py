"""Structure-fixed chunking: target 280 tokens, overlap 60, hard max 380."""

import re
import uuid
from itertools import groupby

from app.services.indexing.chunking.base import (
    ChildChunk,
    ChunkingPolicy,
    ParentNode,
    estimate_tokens,
)
from app.services.parsing.base import Block, Loc, TableBlock, TextBlock


def _loc_key(block: Block, source_type: str) -> tuple:
    """Group key for blocks into parents."""
    if source_type == "pdf":
        return ("page", block.loc.page_num or 0)
    if source_type == "pptx":
        return ("slide", block.loc.slide_num or 0)
    if source_type == "docx":
        hp = block.loc.heading_path or []
        return ("section", tuple(hp))


def _sentences(text: str) -> list[str]:
    """Split text into sentences."""
    return re.split(r'(?<=[.!?])\s+', text) or [text]


def _merge_small_chunks(
    chunks: list[tuple[str, int, int]],
    min_tokens: int = 50,
    max_tokens: int = 380,
) -> list[tuple[str, int, int]]:
    """Merge chunks smaller than min_tokens with next chunk."""
    if not chunks:
        return []
    result: list[tuple[str, int, int]] = []
    acc_text = ""
    acc_start = chunks[0][1]
    acc_end = chunks[0][2]
    for text, start, end in chunks:
        tks = estimate_tokens(text)
        if acc_text and estimate_tokens(acc_text) + tks <= max_tokens and (
            estimate_tokens(acc_text) < min_tokens or tks < min_tokens
        ):
            acc_text = (acc_text + " " + text).strip()
            acc_end = end
        else:
            if acc_text:
                result.append((acc_text, acc_start, acc_end))
            acc_text = text
            acc_start = start
            acc_end = end
    if acc_text:
        result.append((acc_text, acc_start, acc_end))
    return result


class StructureFixedChunkingPolicy(ChunkingPolicy):
    """Fixed token-based chunking with paragraph accumulation."""

    policy_name = "structure_fixed"
    policy_version = "1.0"

    def __init__(
        self,
        target_tokens: int = 280,
        overlap_tokens: int = 60,
        hard_max_tokens: int = 380,
    ):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.hard_max_tokens = hard_max_tokens

    def build_parents(self, blocks: list[Block], source_type: str) -> list[ParentNode]:
        """Group blocks by loc into parents. Includes ImageBlocks for parent grouping."""
        from app.services.parsing.base import ImageBlock

        parent_type = "page" if source_type == "pdf" else "slide" if source_type == "pptx" else "section"
        sorted_blocks = sorted(blocks, key=lambda b: _loc_key(b, source_type))
        parents: list[ParentNode] = []
        seq = 0
        for key, group in groupby(sorted_blocks, key=lambda b: _loc_key(b, source_type)):
            blist = list(group)
            text_parts = []
            for b in blist:
                if isinstance(b, TextBlock):
                    text_parts.append(b.content)
                elif isinstance(b, TableBlock):
                    text_parts.append(b.content)
                # ImageBlock: no text, but parent exists for image pipeline
            parent_text = "\n\n".join(text_parts)
            parent_id = str(uuid.uuid4())
            parents.append(
                ParentNode(
                    parent_id=parent_id,
                    parent_type=parent_type,
                    loc=blist[0].loc if blist else Loc(),
                    parent_text=parent_text,
                    seq_start=seq,
                    seq_end=seq + len(blist) - 1,
                    blocks=blist,
                )
            )
            seq += len(blist)
        return parents

    def build_children(self, parent: ParentNode) -> list[ChildChunk]:
        """Split parent into chunks. Tables become single chunks; text is split."""
        from app.services.parsing.base import ImageBlock

        result: list[ChildChunk] = []
        text_blocks = []
        for b in parent.blocks:
            if isinstance(b, TableBlock):
                result.append(
                    ChildChunk(
                        chunk_id=str(uuid.uuid4()),
                        parent_id=parent.parent_id,
                        chunk_type="table",
                        chunk_text=b.content,
                        embedding_text=b.content,
                        seq_start=parent.seq_start,
                        seq_end=parent.seq_end,
                        loc=parent.loc.to_dict(),
                        chunk_policy=self.policy_name,
                        boundary_signals={"reason": "table_block", "policy_version": self.policy_version},
                        policy_version=self.policy_version,
                    )
                )
            elif isinstance(b, TextBlock):
                text_blocks.append(b)
        text = "\n\n".join(b.content for b in text_blocks)
        if not text.strip():
            return result
        sentences = _sentences(text)
        chunks: list[tuple[str, int, int]] = []
        acc: list[str] = []
        acc_tokens = 0
        seq = 0
        for sent in sentences:
            st = estimate_tokens(sent)
            if acc_tokens + st > self.hard_max_tokens and acc:
                chunk_text = " ".join(acc)
                chunks.append((chunk_text, seq, seq + len(acc) - 1))
                overlap = []
                overlap_tks = 0
                for s in reversed(acc):
                    if overlap_tks + estimate_tokens(s) <= self.overlap_tokens:
                        overlap.insert(0, s)
                        overlap_tks += estimate_tokens(s)
                    else:
                        break
                acc = overlap
                acc_tokens = sum(estimate_tokens(s) for s in acc)
                seq += len(chunk_text.split())
            else:
                acc.append(sent)
                acc_tokens += st
                if acc_tokens >= self.target_tokens:
                    chunk_text = " ".join(acc)
                    chunks.append((chunk_text, parent.seq_start, parent.seq_end))
                    overlap = []
                    overlap_tks = 0
                    for s in reversed(acc):
                        if overlap_tks + estimate_tokens(s) <= self.overlap_tokens:
                            overlap.insert(0, s)
                            overlap_tks += estimate_tokens(s)
                        else:
                            break
                    acc = overlap
                    acc_tokens = sum(estimate_tokens(s) for s in acc)
        if acc:
            chunk_text = " ".join(acc)
            chunks.append((chunk_text, parent.seq_start, parent.seq_end))
        merged = _merge_small_chunks(chunks, min_tokens=50, max_tokens=self.hard_max_tokens)
        for i, (ct, start, end) in enumerate(merged):
            chunk_id = str(uuid.uuid4())
            result.append(
                ChildChunk(
                    chunk_id=chunk_id,
                    parent_id=parent.parent_id,
                    chunk_type="text",
                    chunk_text=ct,
                    embedding_text=ct,
                    seq_start=start,
                    seq_end=end,
                    loc=parent.loc.to_dict(),
                    chunk_policy=self.policy_name,
                    boundary_signals={"reason": "structure_fixed", "policy_version": self.policy_version},
                    policy_version=self.policy_version,
                )
            )
        return result
