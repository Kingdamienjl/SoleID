from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from app.dependencies.auth import get_current_user
from app.schemas.price import PriceSnapshot
from app.services.auth import FirebaseUser
from app.services.cache import get_cache
from app.services.pricing.ebay import EbayPriceProvider

router = APIRouter()


@router.get("/prices", response_model=PriceSnapshot)
async def prices_endpoint(
    sku: str,
    user: FirebaseUser = Depends(get_current_user),
) -> PriceSnapshot:
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
