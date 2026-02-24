"""Image pipeline - OCR and Vision captioning for ImageBlocks."""

import uuid
from typing import Any

from app.config import get_settings
from app.services.indexing.chunking.base import ChildChunk
from app.services.parsing.base import ImageBlock, Loc
from app.services.providers.base import VisionOutput


def _loc_matches(block_loc: Loc, parent_loc: Loc | dict[str, Any]) -> bool:
    """Check if block loc matches parent loc."""
    if hasattr(parent_loc, "to_dict"):
        parent_loc = parent_loc.to_dict()
    if block_loc.page_num is not None and parent_loc.get("page_num") != block_loc.page_num:
        return False
    if block_loc.slide_num is not None and parent_loc.get("slide_num") != block_loc.slide_num:
        return False
    if block_loc.heading_path is not None:
        hp = parent_loc.get("heading_path") or []
        if tuple(block_loc.heading_path) != tuple(hp):
            return False
    return True


def process_image_blocks(
    image_blocks: list[tuple[ImageBlock, str]],
) -> list[ChildChunk]:
    """
    Process image blocks through OCR and/or Vision caption.
    image_blocks: list of (ImageBlock, parent_id)
    Returns list of ChildChunk for image_ocr and image_caption.
    """
    from app.services.providers.registry import get_ocr_provider, get_vision_caption_provider

    settings = get_settings()
    chunks: list[ChildChunk] = []
    ocr_provider = get_ocr_provider() if settings.enable_ocr else None
    vision_provider = get_vision_caption_provider() if settings.enable_vision_caption else None

    for img_block, parent_id in image_blocks:
        loc_dict = img_block.loc.to_dict()
        if ocr_provider and img_block.image_bytes:
            text = ocr_provider.extract_text(img_block.image_bytes)
            if text.strip():
                chunks.append(
                    ChildChunk(
                        chunk_id=str(uuid.uuid4()),
                        parent_id=parent_id,
                        chunk_type="image_ocr",
                        chunk_text=text,
                        embedding_text=text,
                        seq_start=0,
                        seq_end=0,
                        loc=loc_dict,
                        chunk_policy="image_pipeline",
                        boundary_signals={"reason": "ocr"},
                        policy_version="1.0",
                    )
                )
        if vision_provider and img_block.image_bytes:
            out: VisionOutput = vision_provider.caption(img_block.image_bytes)
            caption_text = out.summary
            if out.bullets:
                caption_text += "\n" + "\n".join(f"- {b}" for b in out.bullets)
            if out.entities:
                caption_text += "\nEntities: " + ", ".join(out.entities)
            if out.chart_readout:
                caption_text += f"\nChart: {out.chart_readout}"
            chunks.append(
                ChildChunk(
                    chunk_id=str(uuid.uuid4()),
                    parent_id=parent_id,
                    chunk_type="image_caption",
                    chunk_text=caption_text,
                    embedding_text=caption_text,
                    seq_start=0,
                    seq_end=0,
                    loc=loc_dict,
                    chunk_policy="image_pipeline",
                    boundary_signals={"reason": "vision_caption"},
                    policy_version="1.0",
                )
            )
    return chunks


def find_parent_for_image(image_block: ImageBlock, parents: list[Any]) -> str | None:
    """Find parent_id for an image block by matching loc."""
    for p in parents:
        if _loc_matches(image_block.loc, p.loc.to_dict() if hasattr(p.loc, "to_dict") else p.loc):
            return p.parent_id
    return None
