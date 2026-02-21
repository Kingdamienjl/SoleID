"""
Text-based search endpoints for sneakers.

Provides search functionality by querying Qdrant payload fields
(brand, model, colorway, sku) without requiring image input.

All responses wrapped in ApiResponse envelope for Android app compatibility.
"""
import time
import hashlib
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Any
from pydantic import BaseModel, Field

from app.schemas.shoe import Shoe, SourceRef
from app.services.vector import get_vector_service
from app.services.pricing.sneaks_bridge import get_sneaks_bridge

router = APIRouter()


# ── Android-compatible response models ──────────────────────────

class ApiResponse(BaseModel):
    """Wrapper matching Android ApiResponse<T> data class."""
    success: bool = True
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    code: int = 200
    timestamp: int = 0
    version: str = "1.0"

    class Config:
        # Allow arbitrary types for the 'data' field
        arbitrary_types_allowed = True


class SneakerOut(BaseModel):
    """Sneaker output matching Android Sneaker data class fields."""
    id: int
    name: str
    brand: str
    model: str = ""
    colorway: str = ""
    sku: str = ""
    release_date: str = ""
    retail_price: Optional[float] = None
    description: str = ""
    image_url: str = ""
    images: List[str] = Field(default_factory=list)
    resell_prices: Optional[dict] = None
    category: str = ""
    gender: str = ""
    sizes: List[str] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    popularity_score: float = 0.0
    rating: float = 0.0
    review_count: int = 0


class SearchResponseOut(BaseModel):
    """Search response matching Android SearchResponse<Sneaker>."""
    results: List[SneakerOut]
    query: str
    total_results: int
    search_time: float
    suggestions: List[str] = Field(default_factory=list)
    filters_applied: dict = Field(default_factory=dict)


# ── Helpers ─────────────────────────────────────────────────────

def _shoe_to_sneaker(shoe: Shoe) -> SneakerOut:
    """Convert internal Shoe to Android-compatible SneakerOut."""
    # Generate stable numeric ID from string id
    try:
        numeric_id = int(shoe.id)
    except (ValueError, TypeError):
        numeric_id = int(hashlib.md5(shoe.id.encode()).hexdigest()[:15], 16)

    # Build display name, avoiding duplicate brand prefix
    model = shoe.model
    brand = shoe.brand
    if model.lower().startswith(brand.lower()):
        name = model
    else:
        name = f"{brand} {model}".strip()
    if not name:
        name = shoe.sku

    return SneakerOut(
        id=numeric_id,
        name=name,
        brand=brand,
        model=model,
        colorway=shoe.colorway,
        sku=shoe.sku,
        release_date=shoe.release_date if shoe.release_date else (str(shoe.year) if shoe.year else ""),
        retail_price=shoe.retail_price,
        description=shoe.description,
        image_url=shoe.images[0] if shoe.images else "",
        images=shoe.images,
        resell_prices=shoe.resell_prices,
        gender=shoe.gender,
    )


def _wrap(data: Any, message: str = "") -> dict:
    """Wrap data in ApiResponse envelope."""
    return ApiResponse(
        success=True,
        data=data,
        message=message,
        timestamp=int(time.time() * 1000),
    ).model_dump()


def _wrap_error(error: str, code: int = 500) -> dict:
    """Wrap error in ApiResponse envelope."""
    return ApiResponse(
        success=False,
        error=error,
        code=code,
        timestamp=int(time.time() * 1000),
    ).model_dump()


# ── Internal search helpers ─────────────────────────────────────

def _calculate_relevance(query: str, shoe: Shoe) -> float:
    """Calculate relevance score for a shoe based on query match."""
    score = 0.0
    query_terms = query.lower().split()

    for term in query_terms:
        if term in shoe.brand.lower():
            score += 1.0
        if term in shoe.model.lower():
            score += 0.8
        if term in shoe.colorway.lower():
            score += 0.6
        if term in shoe.sku.lower():
            score += 1.0
        for alias in shoe.aliases:
            if term in alias.lower():
                score += 0.5

    return score


def _sneaks_product_to_shoe(p: dict) -> Shoe:
    """Convert a sneaks-service product dict to an internal Shoe object."""
    # Collect images from multiple sources
    images = []
    if p.get("thumbnail"):
        images.append(p["thumbnail"])
    if isinstance(p.get("images"), dict):
        main_img = p["images"].get("main")
        if main_img and main_img not in images:
            images.append(main_img)
        for extra in p["images"].get("additional", []):
            if extra and extra not in images:
                images.append(extra)

    # Build resell price summary
    resell = p.get("lowestResellPrice") or {}
    resell_prices = {k: v for k, v in resell.items() if v is not None} or None

    # Build source links for StockX/GOAT
    sources = []
    resell_links = p.get("resellLinks") or {}
    if resell_links.get("stockX"):
        sources.append(SourceRef(name="StockX", url=resell_links["stockX"]))
    if resell_links.get("goat"):
        sources.append(SourceRef(name="GOAT", url=resell_links["goat"]))

    return Shoe(
        id=p.get("styleID", ""),
        sku=p.get("styleID", ""),
        brand=p.get("brand", "Unknown"),
        model=p.get("name", ""),
        colorway=p.get("colorway", ""),
        year=int(p["releaseDate"][:4]) if p.get("releaseDate") else None,
        release_date=p.get("releaseDate", ""),
        retail_price=p.get("retailPrice"),
        description=p.get("description", ""),
        resell_prices=resell_prices,
        gender=p.get("gender", ""),
        images=images,
        sources=sources,
        aliases=[],
    )


async def _live_search(
    q: str,
    brand: Optional[str],
    limit: int,
) -> List[tuple]:
    """Search via Sneaks-API bridge. Returns list of (Shoe, score) tuples."""
    try:
        bridge = get_sneaks_bridge()
        products = await bridge.search(q, limit=limit)
        if not products:
            return []

        results = []
        for p in products:
            if brand and p.get("brand", "").lower() != brand.lower():
                continue

            shoe = _sneaks_product_to_shoe(p)
            results.append((shoe, 0.5))

        return results
    except Exception as e:
        import logging
        logging.getLogger("soleid.search").warning("Live search failed: %s", e)
        return []


# ── Endpoints ───────────────────────────────────────────────────

@router.get("/search")
async def search_sneakers(
    q: str = Query(..., min_length=1, description="Search query"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    page: int = Query(1, ge=1, description="Page number (alternative to offset)"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
) -> dict:
    """Search for sneakers by text query."""
    start_time = time.time()
    vector_service = get_vector_service()
    query_lower = q.lower()

    # Use page/per_page if offset wasn't explicitly set
    if offset == 0 and page > 1:
        offset = (page - 1) * per_page
        limit = per_page

    try:
        from qdrant_client.http import models as qmodels

        should_conditions = [
            qmodels.FieldCondition(key="brand", match=qmodels.MatchText(text=query_lower)),
            qmodels.FieldCondition(key="model", match=qmodels.MatchText(text=query_lower)),
            qmodels.FieldCondition(key="colorway", match=qmodels.MatchText(text=query_lower)),
            qmodels.FieldCondition(key="sku", match=qmodels.MatchText(text=query_lower)),
        ]

        must_conditions = []
        if brand:
            must_conditions.append(
                qmodels.FieldCondition(key="brand", match=qmodels.MatchValue(value=brand))
            )

        search_filter = qmodels.Filter(
            should=should_conditions,
            must=must_conditions if must_conditions else None,
        )

        results, _ = vector_service.client.scroll(
            collection_name=vector_service.collection,
            scroll_filter=search_filter,
            limit=limit + offset,
            with_payload=True,
            with_vectors=False,
        )

        paginated_results = results[offset:offset + limit] if offset < len(results) else []

        scored_shoes = []
        for point in paginated_results:
            payload = point.payload or {}
            shoe = Shoe(**payload)
            score = _calculate_relevance(query_lower, shoe)
            scored_shoes.append((shoe, score))

        scored_shoes.sort(key=lambda x: x[1], reverse=True)

        # Supplement with live Sneaks-API if sparse results
        if len(scored_shoes) < 3:
            live_results = await _live_search(q, brand, limit - len(scored_shoes))
            existing_skus = {s.sku.upper() for s, _ in scored_shoes}
            for shoe, score in live_results:
                if shoe.sku.upper() not in existing_skus:
                    scored_shoes.append((shoe, score))
                    existing_skus.add(shoe.sku.upper())
            scored_shoes.sort(key=lambda x: x[1], reverse=True)

        sneakers = [_shoe_to_sneaker(shoe) for shoe, _ in scored_shoes[:limit]]

    except Exception:
        # Qdrant failed - try live search
        live_results = await _live_search(q, brand, limit)
        if live_results:
            sneakers = [_shoe_to_sneaker(shoe) for shoe, _ in live_results]
        else:
            sneakers = []

    search_time = time.time() - start_time

    search_data = SearchResponseOut(
        results=sneakers,
        query=q,
        total_results=len(sneakers),
        search_time=round(search_time, 3),
        suggestions=[],
        filters_applied={"brand": brand} if brand else {},
    ).model_dump()

    return _wrap(search_data)


@router.get("/brands")
async def get_brands() -> dict:
    """Get list of all available brands in the database."""
    vector_service = get_vector_service()

    try:
        results, _ = vector_service.client.scroll(
            collection_name=vector_service.collection,
            limit=10000,
            with_payload=["brand"],
            with_vectors=False,
        )

        brands = set()
        for point in results:
            payload = point.payload or {}
            if "brand" in payload:
                brands.add(payload["brand"])

        brand_list = sorted(list(brands))
        if brand_list:
            return _wrap(brand_list)
    except Exception:
        pass

    # Fallback: return common sneaker brands
    fallback_brands = [
        "Adidas", "Converse", "Jordan", "New Balance",
        "Nike", "Puma", "Reebok", "Vans", "Yeezy",
    ]
    return _wrap(fallback_brands)


@router.get("/sneakers/trending")
async def get_trending_sneakers(
    limit: int = Query(10, ge=1, le=50, description="Number of trending sneakers"),
) -> dict:
    """Get trending/popular sneakers."""
    # Try live trending from Sneaks-API first
    try:
        bridge = get_sneaks_bridge()
        products = await bridge.get_trending(limit=limit)
        if products:
            sneakers = []
            for p in products:
                shoe = _sneaks_product_to_shoe(p)
                sneakers.append(_shoe_to_sneaker(shoe))
            return _wrap(sneakers)
    except Exception:
        pass

    # Fallback to local Qdrant data
    vector_service = get_vector_service()
    try:
        results, _ = vector_service.client.scroll(
            collection_name=vector_service.collection,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        sneakers = []
        for point in results:
            payload = point.payload or {}
            shoe = Shoe(**payload)
            sneakers.append(_shoe_to_sneaker(shoe))

        return _wrap(sneakers)

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch trending: {e}")


@router.get("/sneakers/recent")
async def get_recent_sneakers(
    limit: int = Query(10, ge=1, le=50, description="Number of recent sneakers"),
) -> dict:
    """Get recently added sneakers."""
    return await get_trending_sneakers(limit=limit)


@router.get("/sneakers/{shoe_id}")
async def get_sneaker_by_id(shoe_id: str) -> dict:
    """Get a specific sneaker by Android numeric ID."""
    vector_service = get_vector_service()

    # The Android app uses a numeric ID computed from the shoe's string ID via MD5.
    # Qdrant points are stored with UUID or other string IDs, so we can't retrieve
    # directly — we scroll all payloads and find the matching shoe by recomputing
    # the same numeric ID that _shoe_to_sneaker produces.
    try:
        target_id = int(shoe_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Sneaker not found")

    try:
        results, _ = vector_service.client.scroll(
            collection_name=vector_service.collection,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        for point in results:
            payload = point.payload or {}
            shoe = Shoe(**payload)
            try:
                candidate_id = int(shoe.id)
            except (ValueError, TypeError):
                candidate_id = int(hashlib.md5(shoe.id.encode()).hexdigest()[:15], 16)
            if candidate_id == target_id:
                return _wrap(_shoe_to_sneaker(shoe).model_dump())

        raise HTTPException(status_code=404, detail="Sneaker not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch sneaker: {e}")


@router.get("/brands/{brand}/sneakers")
async def get_sneakers_by_brand(
    brand: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """Get sneakers filtered by brand."""
    vector_service = get_vector_service()
    offset = (page - 1) * per_page

    try:
        from qdrant_client.http import models as qmodels
        results, _ = vector_service.client.scroll(
            collection_name=vector_service.collection,
            scroll_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="brand", match=qmodels.MatchValue(value=brand))]
            ),
            limit=per_page + offset,
            with_payload=True,
            with_vectors=False,
        )
        paginated = results[offset:offset + per_page]
        sneakers = [_shoe_to_sneaker(Shoe(**p.payload)) for p in paginated if p.payload]
        return _wrap(sneakers)
    except Exception:
        pass

    # Fallback: live search
    live = await _live_search(brand, brand=brand, limit=per_page)
    sneakers = [_shoe_to_sneaker(shoe) for shoe, _ in live]
    return _wrap(sneakers)


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="Partial query for suggestions"),
    limit: int = Query(5, ge=1, le=20),
) -> dict:
    """Return search autocomplete suggestions."""
    vector_service = get_vector_service()
    query_lower = q.lower()
    suggestions = set()

    try:
        from qdrant_client.http import models as qmodels
        for field in ("brand", "model"):
            results, _ = vector_service.client.scroll(
                collection_name=vector_service.collection,
                scroll_filter=qmodels.Filter(
                    should=[qmodels.FieldCondition(key=field, match=qmodels.MatchText(text=query_lower))]
                ),
                limit=limit * 3,
                with_payload=[field],
                with_vectors=False,
            )
            for point in results:
                val = (point.payload or {}).get(field, "")
                if val and query_lower in val.lower():
                    suggestions.add(val)
    except Exception:
        pass

    suggestion_list = sorted(suggestions)[:limit]
    return _wrap(suggestion_list)
