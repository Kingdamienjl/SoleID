"""Google Gemini vision provider (primary).

Uses the GEMINI_API_KEY Chris already keeps in K:\\Backup\\Api Keys.
Gemini Flash models have a free tier in AI Studio, which makes this the
cheapest working option: $0 per call within quota. Model is set by
GEMINI_VISION_MODEL (default gemini-2.0-flash).
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

logger = logging.getLogger("soleid.vision.gemini")

_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiVisionProvider(VisionProvider):
    name = "gemini"
    est_cost_usd = 0.0  # free tier within quota

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash")

    async def identify(self, image_bytes: bytes, mime_type: str) -> VisionResult:
        if not self.api_key:
            raise VisionProviderError("GEMINI_API_KEY is not configured")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": IDENTIFY_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode(),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }
        url = f"{_API_ROOT}/{self.model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"x-goog-api-key": self.api_key},
                )
        except httpx.HTTPError as exc:
            raise VisionProviderError(f"gemini request failed: {exc}") from exc
        if resp.status_code != 200:
            raise VisionProviderError(
                f"gemini returned {resp.status_code}: {resp.text[:200]}"
            )
        try:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError) as exc:
            raise VisionProviderError(f"unexpected gemini response shape: {exc}") from exc
        return parse_vision_json(text, model=f"gemini:{self.model}")
