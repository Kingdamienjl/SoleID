"""
StockX API integration for sneaker pricing.

StockX provides real-time market data for sneakers including:
- Lowest Ask (best selling price)
- Highest Bid (best buying offer)
- Last Sale price
- Sales history

API Access:
- Official API requires business partnership
- This implementation supports both official API (when available)
  and a mock mode for development/testing

Environment Variables:
- STOCKX_API_KEY: API key for official access
- STOCKX_ENABLED: Set to "true" to enable (default: false)
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from statistics import median, mean
from typing import List, Optional, Dict, Any

import httpx
from app.schemas.price import PriceSnapshot, SourceBreakdown
from app.services.pricing.base import PriceProvider

logger = logging.getLogger("soleid.pricing.stockx")


class StockXPriceProvider(PriceProvider):
    """StockX pricing provider."""

    BASE_URL = "https://stockx.com/api"
    SEARCH_URL = "https://stockx.com/api/browse"

    def __init__(self) -> None:
        self.api_key = os.getenv("STOCKX_API_KEY", "")
        self.enabled = os.getenv("STOCKX_ENABLED", "false").lower() == "true"
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "SoleID/1.0",
                "Accept": "application/json",
            }
        )
        logger.info("StockX provider initialized (enabled=%s)", self.enabled)

    def is_configured(self) -> bool:
        """Check if StockX API is configured."""
        return self.enabled and bool(self.api_key)

    async def search_product(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a product by SKU or name.

        Args:
            query: SKU or product name to search.

        Returns:
            Product data dict or None if not found.
        """
        if not self.enabled:
            return None

        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            params = {"_search": query, "_limit": 1}
            response = await self.client.get(
                self.SEARCH_URL,
                params=params,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                products = data.get("Products", [])
                if products:
                    return products[0]
            else:
                logger.warning("StockX search failed: %s", response.status_code)

        except Exception as e:
            logger.error("StockX search error: %s", e)

        return None

    async def get_market_data(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get market data for a specific product.

        Args:
            product_id: StockX product UUID.

        Returns:
            Market data dict or None.
        """
        if not self.enabled:
            return None

        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/products/{product_id}/market",
                headers=headers,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning("StockX market data failed: %s", response.status_code)

        except Exception as e:
            logger.error("StockX market error: %s", e)

        return None

    def _generate_mock_data(self, sku: str) -> Dict[str, Any]:
        """Generate realistic mock data for development."""
        base_price = 180 + (hash(sku) % 150)
        volatility = (hash(sku[::-1]) % 30) + 10

        return {
            "lowestAsk": base_price + volatility,
            "highestBid": base_price - volatility // 2,
            "lastSale": base_price + (volatility // 4),
            "salesLast72Hours": 15 + (hash(sku) % 50),
            "changeValue": (hash(sku) % 20) - 10,
            "changePercentage": ((hash(sku) % 20) - 10) / 100,
        }

    async def get_price_snapshot(self, sku: str) -> PriceSnapshot:
        """
        Get price snapshot for a SKU from StockX.

        Args:
            sku: Product SKU to look up.

        Returns:
            PriceSnapshot with StockX market data.
        """
        market_data = None

        if self.enabled:
            # Try to find product by SKU
            product = await self.search_product(sku)
            if product:
                product_id = product.get("uuid") or product.get("id")
                if product_id:
                    market_data = await self.get_market_data(product_id)

        # Fall back to mock data if no real data
        if not market_data:
            if not self.enabled:
                logger.debug("StockX disabled, returning mock data for %s", sku)
            market_data = self._generate_mock_data(sku)

        # Extract pricing info
        lowest_ask = market_data.get("lowestAsk")
        highest_bid = market_data.get("highestBid")
        last_sale = market_data.get("lastSale")

        # Calculate average if we have data
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
                    count=market_data.get("salesLast72Hours"),
                    lowest=highest_bid,
                    highest=lowest_ask,
                )
            ],
        )

    async def get_size_prices(self, sku: str) -> Dict[str, Dict[str, float]]:
        """
        Get prices broken down by size.

        Args:
            sku: Product SKU.

        Returns:
            Dict mapping size to price info.
        """
        if not self.enabled:
            # Return mock size data
            base = 180 + (hash(sku) % 100)
            return {
                "8": {"lowestAsk": base - 10, "highestBid": base - 30},
                "9": {"lowestAsk": base, "highestBid": base - 20},
                "10": {"lowestAsk": base + 15, "highestBid": base - 5},
                "11": {"lowestAsk": base + 10, "highestBid": base - 10},
                "12": {"lowestAsk": base + 5, "highestBid": base - 15},
            }

        # TODO: Implement real size price fetching when API access available
        return {}

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
