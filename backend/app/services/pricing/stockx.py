"""
StockX pricing via Sneaks-API bridge.

Uses the sneaks-service Node.js microservice to get real-time
StockX pricing data from their Algolia search API.

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

logger = logging.getLogger("soleid.pricing.stockx")


class StockXPriceProvider(PriceProvider):
    """StockX pricing provider backed by Sneaks-API bridge."""

    def __init__(self, bridge: Optional[SneaksBridge] = None) -> None:
        self.bridge = bridge or get_sneaks_bridge()
        self.enabled = True  # Always enabled; degrades to mock if bridge down
        logger.info("StockX provider initialized (sneaks-bridge backed)")

    def is_configured(self) -> bool:
        """Check if provider has real data access."""
        return self.bridge.is_available is not False

    async def _search_product(self, sku: str) -> Optional[Dict[str, Any]]:
        """Search for a product by SKU via sneaks-bridge."""
        products = await self.bridge.search(sku, limit=3)
        if not products:
            return None

        # Prefer exact styleID match
        for p in products:
            if p.get("styleID", "").upper() == sku.upper():
                return p
        # Fall back to first result
        return products[0]

    async def _get_detailed_prices(self, style_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed per-size pricing via sneaks-bridge."""
        return await self.bridge.get_prices(style_id)

    def _generate_mock_data(self, sku: str) -> Dict[str, Any]:
        """Generate realistic mock data for development."""
        base_price = 180 + (hash(sku) % 150)
        volatility = (hash(sku[::-1]) % 30) + 10

        return {
            "lowestAsk": base_price + volatility,
            "highestBid": base_price - volatility // 2,
            "lastSale": base_price + (volatility // 4),
            "salesLast72Hours": 15 + (hash(sku) % 50),
        }

    async def get_price_snapshot(self, sku: str) -> PriceSnapshot:
        """
        Get price snapshot for a SKU from StockX.

        Flow:
        1. Search sneaks-service for the product by SKU
        2. Try to get detailed per-size pricing
        3. Fall back to search-result pricing (lowestResellPrice)
        4. Fall back to mock data if service is down
        """
        product = await self._search_product(sku)

        if product:
            # Extract pricing from search result
            lowest_resell = product.get("lowestResellPrice")
            stockx_price = None
            if isinstance(lowest_resell, dict):
                stockx_price = lowest_resell.get("stockX")
            elif isinstance(lowest_resell, (int, float)):
                stockx_price = lowest_resell

            retail = product.get("retailPrice")

            # Try to get detailed pricing
            style_id = product.get("styleID", sku)
            detailed = await self._get_detailed_prices(style_id)

            resell_prices = {}
            if detailed:
                resell_prices = detailed.get("resellPrices", {})

            # If we have per-size prices, compute stats from them
            if resell_prices:
                prices_list = [v for v in resell_prices.values() if v and v > 0]
                lowest = min(prices_list) if prices_list else stockx_price
                highest = max(prices_list) if prices_list else stockx_price
                avg = mean(prices_list) if prices_list else stockx_price
                count = len(prices_list)
            else:
                # Use the lowestResellPrice from search
                lowest = stockx_price
                highest = stockx_price
                avg = stockx_price
                count = 1 if stockx_price else 0

            return PriceSnapshot(
                sku=sku,
                asOf=datetime.now(timezone.utc).isoformat(),
                retail=retail,
                lowestAsk=lowest,
                highestBid=None,
                lastSale=stockx_price,
                averagePrice=avg,
                sourceBreakdown=[
                    SourceBreakdown(
                        source="stockx",
                        median=stockx_price,
                        count=count,
                        lowest=lowest,
                        highest=highest,
                    )
                ],
            )

        # Fallback to mock data
        logger.debug("StockX using mock data for %s (sneaks-service unavailable)", sku)
        mock = self._generate_mock_data(sku)

        lowest_ask = mock["lowestAsk"]
        highest_bid = mock["highestBid"]
        last_sale = mock["lastSale"]
        prices = [p for p in [lowest_ask, highest_bid, last_sale] if p]
        avg_price = mean(prices) if prices else None

        return PriceSnapshot(
            sku=sku,
            asOf=datetime.now(timezone.utc).isoformat(),
            retail=None,
            lowestAsk=lowest_ask,
            highestBid=highest_bid,
            lastSale=last_sale,
            averagePrice=avg_price,
            sourceBreakdown=[
                SourceBreakdown(
                    source="stockx",
                    median=last_sale,
                    count=mock.get("salesLast72Hours"),
                    lowest=highest_bid,
                    highest=lowest_ask,
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
                resell = detailed.get("resellPrices", {})
                if resell:
                    return {
                        size: {"lowestAsk": price}
                        for size, price in resell.items()
                        if price and price > 0
                    }

        # Mock fallback
        base = 180 + (hash(sku) % 100)
        return {
            "8": {"lowestAsk": base - 10},
            "9": {"lowestAsk": base},
            "10": {"lowestAsk": base + 15},
            "11": {"lowestAsk": base + 10},
            "12": {"lowestAsk": base + 5},
        }

    async def close(self) -> None:
        """Close the bridge client."""
        # Bridge is shared; don't close it here
        pass
