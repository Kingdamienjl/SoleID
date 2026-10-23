"""Vision provider selection.

Order: Gemini first (free tier, key already on hand), OpenRouter second
(rotating :free vision models). A provider is only included when its API
key is present in the environment, so deployments light up automatically
once a key is set — no code change needed.
"""
from __future__ import annotations

import logging
import os
from typing import List

from app.services.vision.base import VisionProvider
from app.services.vision.gemini import GeminiVisionProvider
from app.services.vision.openrouter import OpenRouterVisionProvider

logger = logging.getLogger("soleid.vision")

_provider_cache: List[VisionProvider] | None = None


def get_vision_providers() -> List[VisionProvider]:
    global _provider_cache
    if _provider_cache is not None:
        return _provider_cache
    providers: List[VisionProvider] = []
    forced = os.getenv("VISION_PROVIDER", "").strip().lower()
    if os.getenv("GEMINI_API_KEY") and forced in ("", "gemini"):
        providers.append(GeminiVisionProvider())
    if os.getenv("OPENROUTER_API_KEY") and forced in ("", "openrouter"):
        providers.append(OpenRouterVisionProvider())
    logger.info(
        "vision providers configured: %s", [p.name for p in providers] or "none"
    )
    _provider_cache = providers
    return providers
