"""Vision-first shoe identification.

Pipeline per request:
  L1  perceptual-hash cache (exact-ish re-photos skip all model work)
  L2  optional Qdrant cache — the existing CLIP/vector stack, reused as a
      *cache only* (IDENTIFY_QDRANT_CACHE=1, conservative score threshold);
      it is no longer the system of record for identification
  L3  vision provider chain (Gemini -> OpenRouter), budget-guarded

After identification, the style code is verified against the pricing
aggregator: it only counts as verified when a live (non-mock) listing with
a buy URL exists. Low confidence or an unverifiable SKU returns candidate
options instead of one confident answer.
"""
from __future__ import annotations

import io
import json
import logging
import os
from typing import Optional

from PIL import Image

from app.schemas.identify import IdentifyResponse
from app.services.cache import get_cache
from app.services.pricing import get_price_aggregator
from app.services.vision import get_vision_providers
from app.services.vision.base import ShoeCandidate, VisionProviderError
from app.services.vision.budget import BudgetExceeded, check_budget, record_call

logger = logging.getLogger("soleid.identify")

_CACHE_TTL_SECONDS = 30 * 24 * 3600


class NotAShoeError(Exception):
    """The image does not contain a shoe."""


class NoProviderError(Exception):
    """No vision provider is configured or all providers failed."""


def _min_confidence() -> float:
    return float(os.getenv("IDENTIFY_MIN_CONFIDENCE", "0.75"))


def _phash_hex(image_bytes: bytes) -> Optional[str]:
    try:
        import imagehash

        img = Image.open(io.BytesIO(image_bytes))
        return str(imagehash.phash(img))
    except Exception:  # noqa: BLE001
        return None


def _decode_cache_value(raw) -> Optional[dict]:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return raw


async def _l1_lookup(phash: Optional[str]) -> Optional[dict]:
    if not phash:
        return None
    try:
        return _decode_cache_value(await get_cache().get(f"identify:v1:{phash}"))
    except Exception:  # noqa: BLE001
        return None


async def _l1_store(phash: Optional[str], identification: dict) -> None:
    if not phash:
        return
    try:
        await get_cache().set(
            f"identify:v1:{phash}", json.dumps(identification), _CACHE_TTL_SECONDS
        )
    except Exception:  # noqa: BLE001
        logger.debug("identify L1 store failed", exc_info=True)


async def _l2_lookup(image_bytes: bytes) -> Optional[dict]:
    """Qdrant as second-tier cache. Returns an identification dict or None.

    Deliberately conservative: only a near-exact vector hit counts, and any
    failure in the legacy stack silently falls through to the vision path.
    """
    if os.getenv("IDENTIFY_QDRANT_CACHE", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        from app.api.search import _shoe_to_sneaker
        from app.services.embedding import (
            get_embedding_service,
            preprocess_image_for_openclip,
        )
        from app.services.vector import get_vector_service

        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = preprocess_image_for_openclip(pil)
        vector = await get_embedding_service().embed_tensor(tensor)
        results = await get_vector_service().query(vector, top_k=1)
        if not results:
            return None
        top = results[0]
        threshold = float(os.getenv("IDENTIFY_QDRANT_MIN_SCORE", "0.92"))
        if top.score < threshold:
            return None
        sneaker = _shoe_to_sneaker(top.payload)
        primary = {
            "brand": sneaker.brand,
            "name": sneaker.name,
            "colorway": sneaker.colorway,
            "styleId": sneaker.sku,
            "confidence": float(top.score),
        }
        return {"primary": primary, "alternates": []}
    except Exception:  # noqa: BLE001
        logger.debug("identify L2 (qdrant cache) unavailable", exc_info=True)
        return None


async def _vision_identify(image_bytes: bytes, mime_type: str) -> tuple[dict, str]:
    providers = get_vision_providers()
    if not providers:
        raise NoProviderError(
            "no vision provider configured (set GEMINI_API_KEY or OPENROUTER_API_KEY)"
        )
    errors: list[str] = []
    for provider in providers:
        await check_budget(provider.est_cost_usd)  # BudgetExceeded propagates
        try:
            result = await provider.identify(image_bytes, mime_type)
        except VisionProviderError as exc:
            errors.append(f"{provider.name}: {exc}")
            continue
        await record_call(provider.est_cost_usd)
        if not result.is_shoe or result.primary is None:
            raise NotAShoeError("image does not appear to contain a shoe")
        identification = {
            "primary": result.primary.model_dump(),
            "alternates": [a.model_dump() for a in result.alternates],
        }
        return identification, f"vision:{result.model}"
    raise NoProviderError("all vision providers failed: " + "; ".join(errors))


async def _finalize(identification: dict, source: str) -> IdentifyResponse:
    primary = ShoeCandidate(**identification["primary"])
    alternates = [ShoeCandidate(**a) for a in identification.get("alternates", [])]

    prices = None
    sku_verified = False
    if primary.styleId:
        try:
            snapshot = await get_price_aggregator().get_aggregated_prices(
                primary.styleId
            )
            prices = snapshot
            sku_verified = snapshot.dataSource == "live" and any(
                b.buyUrl for b in snapshot.sourceBreakdown
            )
        except Exception:  # noqa: BLE001
            logger.warning("identify pricing lookup failed", exc_info=True)

    confident = primary.confidence >= _min_confidence()
    # A style code that resolves nowhere is treated as unverified even at
    # high model confidence — that is the hallucinated-SKU failure mode.
    verified_or_codeless = sku_verified or not primary.styleId

    if confident and verified_or_codeless:
        return IdentifyResponse(
            shoe=primary,
            candidates=alternates,
            confidence=primary.confidence,
            source=source,
            skuVerified=sku_verified,
            prices=prices,
        )
    return IdentifyResponse(
        shoe=None,
        candidates=[primary, *alternates],
        confidence=primary.confidence,
        source=source,
        skuVerified=sku_verified,
        prices=None,
    )


async def identify_shoe(image_bytes: bytes, mime_type: str) -> IdentifyResponse:
    phash = _phash_hex(image_bytes)

    cached = await _l1_lookup(phash)
    if cached is not None:
        return await _finalize(cached, "cache")

    cached = await _l2_lookup(image_bytes)
    if cached is not None:
        await _l1_store(phash, cached)
        return await _finalize(cached, "qdrant_cache")

    identification, source = await _vision_identify(image_bytes, mime_type)
    await _l1_store(phash, identification)
    return await _finalize(identification, source)
