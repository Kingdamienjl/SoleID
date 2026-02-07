"""
GOAT pricing via Sneaks-API bridge.

Uses the sneaks-service Node.js microservice to get real-time
GOAT pricing data.

Falls back to mock data when the sneaks-service is unavailable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from statistics import mean
from typing import Optional, Dict, Any

from app.schemas.price import PriceSnapshot, SourceBreakdown
from app.services.pricing.base import PriceProvider
from app.services.pricing.sneaks_bridge import SneaksBridge, get_sneaks_bridge

logger = logging.getLogger("soleid.pricing.goat")


class GoatPriceProvider(PriceProvider):
    """GOAT pricing provider backed by Sneaks-API bridge."""

    def __init__(self, bridge: Optional[SneaksBridge] = None) -> None:
        self.bridge = bridge or get_sneaks_bridge()
        self.enabled = True  # Always enabled; degrades to mock if bridge down
        logger.info("GOAT provider initialized (sneaks-bridge backed)")

    def is_configured(self) -> bool:
        """Check if provider has real data access."""
        return self.bridge.is_available is not False

    async def _search_product(self, sku: str) -> Optional[Dict[str, Any]]:
        """Search for a product by SKU via sneaks-bridge."""
        products = await self.bridge.search(sku, limit=3)
        if not products:
            return None

        for p in products:
            if p.get("styleID", "").upper() == sku.upper():
                return p
        return products[0]

    async def _get_detailed_prices(self, style_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed per-size pricing via sneaks-bridge."""
        return await self.bridge.get_prices(style_id)

    def _generate_mock_data(self, sku: str) -> Dict[str, Any]:
        """Generate realistic mock data for development."""
        base_price = 175 + (hash(sku) % 160)
        variance = (hash(sku[::-1]) % 25) + 8

        return {
            "lowestPriceNew": base_price + variance,
            "lowestPriceUsed": base_price - variance,
            "instantShipPrice": base_price + variance + 20,
            "lastSale": base_price + (variance // 3),
            "numberOfListings": 25 + (hash(sku) % 100),
            "retailPrice": 170 + (hash(sku) % 80),
        }

    async def get_price_snapshot(self, sku: str) -> PriceSnapshot:
        """
        Get price snapshot for a SKU from GOAT.

        Flow:
        1. Search sneaks-service for the product by SKU
        2. Try to get detailed per-size GOAT pricing
        3. Fall back to search-result pricing (lowestResellPrice.goat)
        4. Fall back to mock data if service is down
        """
        product = await self._search_product(sku)

        if product:
            # Extract GOAT pricing from search result
            lowest_resell = product.get("lowestResellPrice")
            goat_price = None
            if isinstance(lowest_resell, dict):
                goat_price = lowest_resell.get("goat")

            retail = product.get("retailPrice")

            # Try to get detailed GOAT pricing
            style_id = product.get("styleID", sku)
            detailed = await self._get_detailed_prices(style_id)

            goat_prices = {}
            images = []
            if detailed:
                goat_prices = detailed.get("goatPrices", {})
                img_data = detailed.get("images", {})
                images = img_data.get("additional", [])

            # If we have per-size prices, compute stats from them
            if goat_prices:
                prices_list = [v for v in goat_prices.values() if v and v > 0]
                lowest = min(prices_list) if prices_list else goat_price
                highest = max(prices_list) if prices_list else goat_price
                avg = mean(prices_list) if prices_list else goat_price
                count = len(prices_list)
            else:
                lowest = goat_price
                highest = goat_price
                avg = goat_price
                count = 1 if goat_price else 0

            return PriceSnapshot(
                sku=sku,
                asOf=datetime.now(timezone.utc).isoformat(),
                retail=retail,
                lowestAsk=lowest,
                highestBid=None,  # GOAT doesn't have a bid system
                lastSale=goat_price,
                averagePrice=avg,
                sourceBreakdown=[
                    SourceBreakdown(
                        source="goat",
                        median=goat_price,
                        count=count,
                        lowest=lowest,
                        highest=highest,
                    )
                ],
            )

        # Fallback to mock data
        logger.debug("GOAT using mock data for %s (sneaks-service unavailable)", sku)
        mock = self._generate_mock_data(sku)

        lowest_new = mock["lowestPriceNew"]
        last_sale = mock["lastSale"]
        retail = mock["retailPrice"]

        prices = [p for p in [lowest_new, last_sale] if p and p > 0]
        avg_price = mean(prices) if prices else None

        return PriceSnapshot(
            sku=sku,
            asOf=datetime.now(timezone.utc).isoformat(),
            retail=retail,
            lowestAsk=lowest_new,
            highestBid=None,
            lastSale=last_sale,
            averagePrice=avg_price,
            sourceBreakdown=[
                SourceBreakdown(
                    source="goat",
                    median=last_sale,
                    count=mock.get("numberOfListings"),
                    lowest=mock.get("lowestPriceUsed"),
                    highest=mock.get("instantShipPrice"),
                )
            ],
        )

    async def get_size_prices(self, sku: str) -> Dict[str, Dict[str, float]]:
        """Get prices broken down by size."""
        product = await self._search_product(sku)
        if product:
            style_id = product.get("styleID", sku)
            detailed = await self._get_detailed_prices(style_id)
            if detailed:
                goat = detailed.get("goatPrices", {})
                if goat:
                    return {
                        size: {"new": price}
                        for size, price in goat.items()
                        if price and price > 0
                    }

        # Mock fallback
        base = 175 + (hash(sku) % 100)
        return {
            "8": {"new": base - 5},
            "9": {"new": base + 5},
            "10": {"new": base + 20},
            "11": {"new": base + 15},
            "12": {"new": base + 10},
        }

    async def close(self) -> None:
        """Close the bridge client."""
        pass
