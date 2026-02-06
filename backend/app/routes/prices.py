"""
Price endpoints for sneaker market data.

Provides aggregated pricing from multiple marketplaces:
- StockX: Real-time market data
- GOAT: New and used prices
- eBay: Sold listing history
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.dependencies.auth import get_current_user
from app.schemas.price import PriceSnapshot
from app.services.auth import FirebaseUser
from app.services.cache import get_cache
from app.services.pricing import get_price_aggregator

router = APIRouter(tags=["Prices"])


@router.get("/prices", response_model=PriceSnapshot)
async def get_prices(
    sku: str = Query(..., description="Product SKU to look up"),
    sources: Optional[str] = Query(
        None,
        description="Comma-separated list of sources: stockx,goat,ebay. Default: all"
    ),
    user: FirebaseUser = Depends(get_current_user),
) -> PriceSnapshot:
    """
    Get aggregated prices for a sneaker SKU.

    Combines data from multiple marketplaces to provide:
    - Lowest asking price across all platforms
    - Highest bid (where available)
    - Recent sale prices
    - Source-by-source breakdown

    **Requires authentication.**
    """
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")

    # Parse sources
    include_sources = None
    if sources:
        include_sources = [s.strip().lower() for s in sources.split(",")]
        valid_sources = {"stockx", "goat", "ebay"}
        invalid = set(include_sources) - valid_sources
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sources: {invalid}. Valid: stockx, goat, ebay"
            )

    # Check cache
    cache = get_cache()
    cache_key = f"prices:{sku}:{sources or 'all'}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Fetch aggregated prices
    aggregator = get_price_aggregator()
    snapshot = await aggregator.get_aggregated_prices(sku, include_sources)

    snapshot.asOf = datetime.now(timezone.utc).isoformat()
    await cache.set(cache_key, snapshot, ttl_seconds=300)  # 5 min cache

    return snapshot


@router.get("/prices/compare")
async def compare_prices(
    sku: str = Query(..., description="Product SKU to compare"),
    user: FirebaseUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get side-by-side price comparison from all marketplaces.

    Shows prices from each source individually for easy comparison.

    **Requires authentication.**
    """
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")

    cache = get_cache()
    cache_key = f"prices:compare:{sku}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    aggregator = get_price_aggregator()
    comparison = await aggregator.get_price_comparison(sku)

    await cache.set(cache_key, comparison, ttl_seconds=300)
    return comparison


@router.get("/prices/best")
async def get_best_price(
    sku: str = Query(..., description="Product SKU to find best price"),
    user: FirebaseUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Find the best (lowest) price across all marketplaces.

    Returns the best price and which platform offers it.

    **Requires authentication.**
    """
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")

    cache = get_cache()
    cache_key = f"prices:best:{sku}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    aggregator = get_price_aggregator()
    best = await aggregator.get_best_price(sku)

    await cache.set(cache_key, best, ttl_seconds=300)
    return best


@router.get("/prices/sources")
async def list_price_sources() -> Dict[str, Any]:
    """
    List available price data sources and their status.

    No authentication required.
    """
    aggregator = get_price_aggregator()

    return {
        "sources": [
            {
                "name": "stockx",
                "displayName": "StockX",
                "description": "Real-time market data with lowest ask, highest bid, and sales history",
                "enabled": aggregator.stockx.enabled,
                "configured": aggregator.stockx.is_configured(),
            },
            {
                "name": "goat",
                "displayName": "GOAT",
                "description": "New and used sneaker prices with instant ship options",
                "enabled": aggregator.goat.enabled,
                "configured": aggregator.goat.is_configured(),
            },
            {
                "name": "ebay",
                "displayName": "eBay",
                "description": "Sold listing history and market trends",
                "enabled": True,  # eBay mock always available
                "configured": aggregator.ebay.is_configured(),
            },
        ],
        "note": "Sources with configured=false will return mock data for development",
    }
