"""
Text-based search endpoints for sneakers.

Provides search functionality by querying Qdrant payload fields
(brand, model, colorway, sku) without requiring image input.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.shoe import Shoe
from app.services.vector import get_vector_service
from app.services.pricing.sneaks_bridge import get_sneaks_bridge

router = APIRouter()


class SearchResult(BaseModel):
    """Single search result with relevance score."""
    shoe: Shoe
    score: float


class SearchResponse(BaseModel):
    """Search response containing results and metadata."""
    results: List[SearchResult]
    total: int
    query: str
    filters: dict


class BrandsResponse(BaseModel):
    """Response containing list of available brands."""
    brands: List[str]
    total: int


class TrendingResponse(BaseModel):
    """Response containing trending/popular shoes."""
    shoes: List[Shoe]
    total: int


@router.get("/search", response_model=SearchResponse)
async def search_sneakers(
    q: str = Query(..., min_length=1, description="Search query"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> SearchResponse:
    """
    Search for sneakers by text query.

    Searches across brand, model, colorway, SKU, and aliases.
    Results are sorted by relevance.

    - **q**: Search query (required)
    - **brand**: Filter results to specific brand (optional)
    - **limit**: Maximum number of results (default: 20, max: 100)
    - **offset**: Pagination offset (default: 0)
    """
    vector_service = get_vector_service()
    query_lower = q.lower()

    try:
        # Use Qdrant scroll with filtering to search by payload
        # This searches the stored shoe metadata
        from qdrant_client.http import models as qmodels

        # Build filter conditions
        must_conditions = []

        # Text search across multiple fields using match
        should_conditions = [
            qmodels.FieldCondition(
                key="brand",
                match=qmodels.MatchText(text=query_lower),
            ),
            qmodels.FieldCondition(
                key="model",
                match=qmodels.MatchText(text=query_lower),
            ),
            qmodels.FieldCondition(
                key="colorway",
                match=qmodels.MatchText(text=query_lower),
            ),
            qmodels.FieldCondition(
                key="sku",
                match=qmodels.MatchText(text=query_lower),
            ),
        ]

        # Add brand filter if specified
        if brand:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="brand",
                    match=qmodels.MatchValue(value=brand),
                )
            )

        # Build the filter
        search_filter = qmodels.Filter(
            should=should_conditions,
            must=must_conditions if must_conditions else None,
        )

        # Scroll through results with filter
        results, _ = vector_service.client.scroll(
            collection_name=vector_service.collection,
            scroll_filter=search_filter,
            limit=limit + offset,
            with_payload=True,
            with_vectors=False,
        )

        # Apply offset and convert to response format
        paginated_results = results[offset:offset + limit] if offset < len(results) else []

        search_results = []
        for point in paginated_results:
            payload = point.payload or {}
            shoe = Shoe(**payload)
            # Calculate simple relevance score based on field matches
            score = _calculate_relevance(query_lower, shoe)
            search_results.append(SearchResult(shoe=shoe, score=score))

        # Sort by score descending
        search_results.sort(key=lambda x: x.score, reverse=True)

        # If local results are sparse, supplement with live Sneaks-API data
        if len(search_results) < 3:
            live_results = await _live_search(q, brand, limit - len(search_results))
            existing_skus = {r.shoe.sku.upper() for r in search_results}
            for lr in live_results:
                if lr.shoe.sku.upper() not in existing_skus:
                    search_results.append(lr)
                    existing_skus.add(lr.shoe.sku.upper())
            search_results.sort(key=lambda x: x.score, reverse=True)

        return SearchResponse(
            results=search_results[:limit],
            total=len(search_results),
            query=q,
            filters={"brand": brand} if brand else {},
        )

    except Exception as e:
        # If Qdrant search fails entirely, try live search as primary
        live_results = await _live_search(q, brand, limit)
        if live_results:
            return SearchResponse(
                results=live_results,
                total=len(live_results),
                query=q,
                filters={"brand": brand} if brand else {},
            )
        # Fall back to in-memory search
        return await _fallback_search(q, brand, limit, offset)


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
            score += 1.0  # SKU exact match is high value
        for alias in shoe.aliases:
            if term in alias.lower():
                score += 0.5

    return score


async def _fallback_search(
    q: str,
    brand: Optional[str],
    limit: int,
    offset: int
) -> SearchResponse:
    """Fallback search by fetching all shoes and filtering in memory."""
    vector_service = get_vector_service()
    query_lower = q.lower()

    try:
        # Fetch all points (limited to reasonable amount)
        results, _ = vector_service.client.scroll(
            collection_name=vector_service.collection,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )

        # Filter in memory
        matching = []
        for point in results:
            payload = point.payload or {}
            shoe = Shoe(**payload)

            # Check if query matches any field
            searchable = f"{shoe.brand} {shoe.model} {shoe.colorway} {shoe.sku} {' '.join(shoe.aliases)}".lower()
            if query_lower in searchable:
                # Apply brand filter
                if brand and shoe.brand.lower() != brand.lower():
                    continue

                score = _calculate_relevance(query_lower, shoe)
                matching.append(SearchResult(shoe=shoe, score=score))

        # Sort by score
        matching.sort(key=lambda x: x.score, reverse=True)

        # Apply pagination
        paginated = matching[offset:offset + limit]

        return SearchResponse(
            results=paginated,
            total=len(matching),
            query=q,
            filters={"brand": brand} if brand else {},
        )

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Search unavailable: {e}")


async def _live_search(
    q: str,
    brand: Optional[str],
    limit: int,
) -> List[SearchResult]:
    """Search via Sneaks-API bridge for live StockX/GOAT results."""
    try:
        bridge = get_sneaks_bridge()
        products = await bridge.search(q, limit=limit)
        if not products:
            return []

        results = []
        for p in products:
            # Apply brand filter if specified
            if brand and p.get("brand", "").lower() != brand.lower():
                continue

            shoe = Shoe(
                id=p.get("styleID", ""),
                sku=p.get("styleID", ""),
                brand=p.get("brand", "Unknown"),
                model=p.get("name", ""),
                colorway=p.get("colorway", ""),
                year=int(p["releaseDate"][:4]) if p.get("releaseDate") else None,
                images=[p["thumbnail"]] if p.get("thumbnail") else [],
                sources=[],
                aliases=[],
            )
            results.append(SearchResult(shoe=shoe, score=0.5))

        return results
    except Exception as e:
        import logging
        logging.getLogger("soleid.search").warning("Live search failed: %s", e)
        return []


@router.get("/brands", response_model=BrandsResponse)
async def get_brands() -> BrandsResponse:
    """
    Get list of all available brands in the database.
    """
    vector_service = get_vector_service()

    try:
        # Fetch all points to extract unique brands
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

        return BrandsResponse(
            brands=brand_list,
            total=len(brand_list),
        )

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch brands: {e}")


@router.get("/sneakers/trending", response_model=TrendingResponse)
async def get_trending_sneakers(
    limit: int = Query(10, ge=1, le=50, description="Number of trending sneakers to return"),
) -> TrendingResponse:
    """
    Get trending/popular sneakers.

    Uses live Sneaks-API data (StockX trending) with local DB fallback.
    """
    # Try live trending from Sneaks-API first
    try:
        bridge = get_sneaks_bridge()
        products = await bridge.get_trending(limit=limit)
        if products:
            shoes = []
            for p in products:
                shoe = Shoe(
                    id=p.get("styleID", ""),
                    sku=p.get("styleID", ""),
                    brand=p.get("brand", "Unknown"),
                    model=p.get("name", ""),
                    colorway=p.get("colorway", ""),
                    year=int(p["releaseDate"][:4]) if p.get("releaseDate") else None,
                    images=[p["thumbnail"]] if p.get("thumbnail") else [],
                    sources=[],
                    aliases=[],
                )
                shoes.append(shoe)
            return TrendingResponse(shoes=shoes, total=len(shoes))
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

        shoes = []
        for point in results:
            payload = point.payload or {}
            shoes.append(Shoe(**payload))

        return TrendingResponse(shoes=shoes, total=len(shoes))

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch trending: {e}")


@router.get("/sneakers/recent", response_model=TrendingResponse)
async def get_recent_sneakers(
    limit: int = Query(10, ge=1, le=50, description="Number of recent sneakers to return"),
) -> TrendingResponse:
    """
    Get recently added sneakers.
    """
    # Same as trending for now - in production would sort by creation date
    return await get_trending_sneakers(limit=limit)


@router.get("/sneakers/{shoe_id}", response_model=Shoe)
async def get_sneaker_by_id(shoe_id: str) -> Shoe:
    """
    Get a specific sneaker by ID.
    """
    vector_service = get_vector_service()

    try:
        # Retrieve point by ID
        points = vector_service.client.retrieve(
            collection_name=vector_service.collection,
            ids=[shoe_id],
            with_payload=True,
            with_vectors=False,
        )

        if not points:
            raise HTTPException(status_code=404, detail="Sneaker not found")

        payload = points[0].payload or {}
        return Shoe(**payload)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch sneaker: {e}")
