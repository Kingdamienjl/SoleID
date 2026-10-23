"""Shared types, prompt, and parsing for vision identification providers."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field


class VisionProviderError(Exception):
    """Raised when a vision provider cannot produce a usable result."""


class ShoeCandidate(BaseModel):
    brand: str
    name: str
    colorway: Optional[str] = None
    styleId: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class VisionResult(BaseModel):
    is_shoe: bool
    primary: Optional[ShoeCandidate] = None
    alternates: List[ShoeCandidate] = []
    model: str = ""


IDENTIFY_PROMPT = """You are a sneaker identification expert. Look at the photo and identify the shoe.

Return ONLY a JSON object with exactly this shape:
{
  "isShoe": true,
  "brand": "Nike",
  "name": "Air Jordan 1 Retro High OG",
  "colorway": "Chicago Lost and Found",
  "styleId": "DZ5485-612",
  "confidence": 0.93,
  "alternates": [
    {"brand": "...", "name": "...", "colorway": "...", "styleId": null, "confidence": 0.4}
  ]
}

Rules:
- If the image does not show a shoe/sneaker, return {"isShoe": false}.
- "styleId" is the manufacturer style code (e.g. DD1391-100). Use null when you
  are not confident in the exact code — never guess a code to fill the field.
- "confidence" reflects certainty about the exact model AND colorway, not just
  the brand. Similar colorways of the same silhouette should lower it.
- "alternates" holds up to 2 other plausible identifications, best first.
- No prose, no markdown — JSON only."""


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_vision_json(text: str, model: str) -> VisionResult:
    """Parse a provider's text response into a VisionResult, tolerating fences."""
    cleaned = _FENCE_RE.sub("", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise VisionProviderError(f"provider returned non-JSON output: {exc}") from exc

    if not data.get("isShoe"):
        return VisionResult(is_shoe=False, model=model)

    try:
        primary = ShoeCandidate(
            brand=data["brand"],
            name=data["name"],
            colorway=data.get("colorway"),
            styleId=data.get("styleId"),
            confidence=float(data.get("confidence", 0.0)),
        )
        alternates = [
            ShoeCandidate(**alt) for alt in (data.get("alternates") or [])[:2]
        ]
    except Exception as exc:  # noqa: BLE001
        raise VisionProviderError(f"provider JSON missing fields: {exc}") from exc

    return VisionResult(
        is_shoe=True, primary=primary, alternates=alternates, model=model
    )


class VisionProvider(ABC):
    """One vision identification backend. Implementations must be swappable
    via environment config only — no call-site changes."""

    name: str = "base"
    est_cost_usd: float = 0.0  # estimated cost per identify call, for budgeting

    @abstractmethod
    async def identify(self, image_bytes: bytes, mime_type: str) -> VisionResult:
        """Identify the shoe in an image. Raises VisionProviderError on failure."""
        raise NotImplementedError
