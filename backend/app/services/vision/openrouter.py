"""OpenRouter vision provider (fallback).

Uses OPENROUTER_API_KEY. Models are tried in order from
OPENROUTER_VISION_MODELS (comma-separated); the defaults prefer :free
vision models, whose availability rotates — a paid cheap model is last
so the chain still lands somewhere that works.
"""
from __future__ import annotations

import base64
import logging
import os

import httpx

from app.services.vision.base import (
    IDENTIFY_PROMPT,
    VisionProvider,
    VisionProviderError,
    VisionResult,
    parse_vision_json,
)

logger = logging.getLogger("soleid.vision.openrouter")

_API_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODELS = (
    "meta-llama/llama-3.2-11b-vision-instruct:free,"
    "qwen/qwen-2.5-vl-7b-instruct:free,"
    "google/gemini-2.0-flash-001"
)


class OpenRouterVisionProvider(VisionProvider):
    name = "openrouter"
    est_cost_usd = 0.002  # worst-case cheap paid model; :free models cost 0

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        models = os.getenv("OPENROUTER_VISION_MODELS", _DEFAULT_MODELS)
        self.models = [m.strip() for m in models.split(",") if m.strip()]

    async def identify(self, image_bytes: bytes, mime_type: str) -> VisionResult:
        if not self.api_key:
            raise VisionProviderError("OPENROUTER_API_KEY is not configured")
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"
        errors: list[str] = []
        for model in self.models:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": IDENTIFY_PROMPT},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        _API_URL,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
            except httpx.HTTPError as exc:
                errors.append(f"{model}: {exc}")
                continue
            if resp.status_code != 200:
                errors.append(f"{model}: HTTP {resp.status_code}")
                continue
            try:
                text = resp.json()["choices"][0]["message"]["content"]
                return parse_vision_json(text, model=f"openrouter:{model}")
            except (KeyError, IndexError, ValueError, VisionProviderError) as exc:
                errors.append(f"{model}: {exc}")
                continue
        raise VisionProviderError(
            "all openrouter models failed: " + "; ".join(errors)
        )
