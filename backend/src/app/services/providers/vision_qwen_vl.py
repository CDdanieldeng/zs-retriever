"""Qwen-VL Vision caption provider via DashScope API."""

import base64
import json
import os
import re
from typing import Any

import httpx

from app.services.providers.base import VisionCaptionProvider, VisionOutput


def _detect_image_mime(image_bytes: bytes) -> str:
    """Detect image MIME type from magic bytes."""
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"  # fallback


# Prompt for structured caption output (JSON)
_CAPTION_PROMPT = """请描述这张图片，以JSON格式返回，格式如下：
{"summary": "简要概括图片内容", "bullets": ["要点1", "要点2"], "entities": ["实体1", "实体2"], "chart_readout": "如是图表则读出数据，否则为null"}

要求：
- summary: 必填，一句话概括
- bullets: 数组，重要要点，无则[]
- entities: 数组，关键实体（人物、组织、产品等），无则[]
- chart_readout: 如是图表/表格则读出数据，否则null
只返回JSON，不要其他文字。"""


class QwenVisionCaptionProvider(VisionCaptionProvider):
    """Vision caption via DashScope Qwen3-VL-Flash API."""

    DEFAULT_MODEL = "qwen3-vl-flash"
    API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Args:
            api_key: DashScope API key, default from DASHSCOPE_API_KEY env
            base_url: Override API base URL (e.g. dashscope-intl for Singapore)
            model: Model name, default qwen3-vl-flash
        """
        from app.config import get_settings

        settings = get_settings()
        self._api_key = (
            api_key or os.getenv("DASHSCOPE_API_KEY", "") or ""
        ).strip()
        self._base_url = (
            base_url
            or getattr(settings, "vision_qwen_api_base_url", None)
            or self.API_URL
        )
        self._model = (
            model
            or getattr(settings, "vision_qwen_api_model", None)
            or self.DEFAULT_MODEL
        )

    def caption(self, image_bytes: bytes) -> VisionOutput:
        """Generate caption via Qwen3-VL-Flash API."""
        if not self._api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY is not set. Add it to backend/.env or set the env var."
            )
        if not image_bytes:
            return VisionOutput(
                summary="[Empty image]",
                bullets=[],
                entities=[],
                chart_readout=None,
            )

        mime = _detect_image_mime(image_bytes)
        b64 = _bytes_to_base64(image_bytes)
        data_url = f"data:{mime};base64,{b64}"

        url = f"{self._base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _CAPTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
            "max_tokens": 1024,
        }

        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data.get("choices")
        if not choice:
            return VisionOutput(
                summary="[API returned no choices]",
                bullets=[],
                entities=[],
                chart_readout=None,
            )

        content = choice[0].get("message", {}).get("content") or ""
        return _parse_vision_response(content)


def _bytes_to_base64(data: bytes) -> str:
    """Encode bytes to base64 string."""
    return base64.b64encode(data).decode("ascii")


def _parse_vision_response(content: str) -> VisionOutput:
    """Parse API response into VisionOutput. Fallback to raw text if JSON fails."""
    content = content.strip()
    # Try to extract JSON block (model might wrap in ```json ... ```)
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if json_match:
        content = json_match.group(1).strip()

    # Try parse as JSON
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            summary = str(obj.get("summary", "")).strip() or "[无描述]"
            bullets = obj.get("bullets")
            if isinstance(bullets, list):
                bullets = [str(b).strip() for b in bullets if str(b).strip()]
            else:
                bullets = []
            entities = obj.get("entities")
            if isinstance(entities, list):
                entities = [str(e).strip() for e in entities if str(e).strip()]
            else:
                entities = []
            chart = obj.get("chart_readout")
            chart_readout = str(chart).strip() if chart is not None and str(chart).strip() and str(chart).lower() != "null" else None
            return VisionOutput(
                summary=summary,
                bullets=bullets,
                entities=entities,
                chart_readout=chart_readout,
            )
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: use raw content as summary
    return VisionOutput(
        summary=content[:2000] if content else "[解析失败]",
        bullets=[],
        entities=[],
        chart_readout=None,
    )
