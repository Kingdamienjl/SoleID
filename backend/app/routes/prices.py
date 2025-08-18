from fastapi import APIRouter, HTTPException
from app.schemas.price import PriceSnapshot
from app.services.pricing.ebay import EbayPriceProvider
from app.services.cache import get_cache
from datetime import datetime, timezone

router = APIRouter()


@router.get("/prices", response_model=PriceSnapshot)
async def prices_endpoint(sku: str) -> PriceSnapshot:
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")

    cache = get_cache()
    cache_key = f"prices:{sku}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    provider = EbayPriceProvider()
    snapshot = await provider.get_price_snapshot(sku)

    snapshot.asOf = datetime.now(timezone.utc).isoformat()
    await cache.set(cache_key, snapshot, ttl_seconds=600)
    return snapshot
