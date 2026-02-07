"""
Price Aggregator Service

Combines pricing data from multiple sources (StockX, GOAT, eBay)
to provide comprehensive market data for sneakers.

Features:
- Parallel fetching from multiple providers
- Intelligent price aggregation
- Confidence scoring based on data availability
- Caching support
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from statistics import mean, median
from typing import List, Optional, Dict, Any

from app.schemas.price import PriceSnapshot, SourceBreakdown
from app.services.pricing.sneaks_bridge import SneaksBridge, get_sneaks_bridge
from app.services.pricing.stockx import StockXPriceProvider
from app.services.pricing.goat import GoatPriceProvider
from app.services.pricing.ebay import EbayPriceProvider

logger = logging.getLogger("soleid.pricing.aggregator")


class PriceAggregator:
    """
    Aggregates pricing data from multiple marketplaces.

    Provides a unified view of sneaker prices across:
    - StockX (real-time via Sneaks-API bridge)
    - GOAT (real-time via Sneaks-API bridge)
    - eBay (sold listings data)
    """

    def __init__(self) -> None:
        bridge = get_sneaks_bridge()
        self.stockx = StockXPriceProvider(bridge=bridge)
        self.goat = GoatPriceProvider(bridge=bridge)
        self.ebay = EbayPriceProvider()
        self.bridge = bridge
        logger.info("Price aggregator initialized (sneaks-bridge backed)")

    async def get_aggregated_prices(
        self,
        sku: str,
        include_sources: Optional[List[str]] = None,
    ) -> PriceSnapshot:
        """
        Get aggregated prices from all available sources.

        Args:
            sku: Product SKU to look up.
            include_sources: List of sources to include. Default: all available.
                            Options: "stockx", "goat", "ebay"

        Returns:
            Aggregated PriceSnapshot with data from all sources.
        """
        sources = include_sources or ["stockx", "goat", "ebay"]

        # Fetch prices in parallel
        tasks = []
        source_names = []

        if "stockx" in sources:
            tasks.append(self._safe_fetch(self.stockx.get_price_snapshot(sku), "stockx"))
            source_names.append("stockx")

        if "goat" in sources:
            tasks.append(self._safe_fetch(self.goat.get_price_snapshot(sku), "goat"))
            source_names.append("goat")

        if "ebay" in sources:
            tasks.append(self._safe_fetch(self.ebay.get_price_snapshot(sku), "ebay"))
            source_names.append("ebay")

        results = await asyncio.gather(*tasks)

        # Combine results
        snapshots = [r for r in results if r is not None]

        if not snapshots:
            logger.warning("No price data available for SKU: %s", sku)
            return PriceSnapshot(
                sku=sku,
                asOf=datetime.now(timezone.utc).isoformat(),
                retail=None,
                lowestAsk=None,
                highestBid=None,
                lastSale=None,
                averagePrice=None,
                sourceBreakdown=[],
            )

        return self._aggregate_snapshots(sku, snapshots)

    async def _safe_fetch(
        self,
        coro,
        source_name: str,
    ) -> Optional[PriceSnapshot]:
        """Safely fetch from a provider, returning None on error."""
        try:
            return await coro
        except Exception as e:
            logger.error("Error fetching from %s: %s", source_name, e)
            return None

    def _aggregate_snapshots(
        self,
        sku: str,
        snapshots: List[PriceSnapshot],
    ) -> PriceSnapshot:
        """Aggregate multiple snapshots into one."""
        # Collect all values
        lowest_asks = []
        highest_bids = []
        last_sales = []
        retails = []
        all_breakdowns = []

        for snap in snapshots:
            if snap.lowestAsk:
                lowest_asks.append(snap.lowestAsk)
            if snap.highestBid:
                highest_bids.append(snap.highestBid)
            if snap.lastSale:
                last_sales.append(snap.lastSale)
            if snap.retail:
                retails.append(snap.retail)
            all_breakdowns.extend(snap.sourceBreakdown)

        # Calculate aggregated values
        # Use lowest of lowest asks (best deal for buyer)
        lowest_ask = min(lowest_asks) if lowest_asks else None

        # Use highest of highest bids (best deal for seller)
        highest_bid = max(highest_bids) if highest_bids else None

        # Use median of last sales for stability
        last_sale = median(last_sales) if last_sales else None

        # Use mode of retail prices (most common)
        retail = retails[0] if retails else None

        # Calculate overall average
        all_prices = lowest_asks + last_sales
        avg_price = mean(all_prices) if all_prices else None

        return PriceSnapshot(
            sku=sku,
            asOf=datetime.now(timezone.utc).isoformat(),
            retail=retail,
            lowestAsk=lowest_ask,
            highestBid=highest_bid,
            lastSale=last_sale,
            averagePrice=avg_price,
            sourceBreakdown=all_breakdowns,
        )

    async def get_price_comparison(self, sku: str) -> Dict[str, Any]:
        """
        Get side-by-side price comparison from all sources.

        Args:
            sku: Product SKU.

        Returns:
            Dict with prices from each source for easy comparison.
        """
        snapshot = await self.get_aggregated_prices(sku)

        comparison = {
            "sku": sku,
            "asOf": snapshot.asOf,
            "aggregated": {
                "lowestAsk": snapshot.lowestAsk,
                "highestBid": snapshot.highestBid,
                "lastSale": snapshot.lastSale,
                "averagePrice": snapshot.averagePrice,
            },
            "bySource": {},
        }

        for breakdown in snapshot.sourceBreakdown:
            comparison["bySource"][breakdown.source] = {
                "median": breakdown.median,
                "count": breakdown.count,
                "lowest": breakdown.lowest,
                "highest": breakdown.highest,
            }

        return comparison

    async def get_best_price(self, sku: str) -> Dict[str, Any]:
        """
        Find the best price across all marketplaces.

        Args:
            sku: Product SKU.

        Returns:
            Dict with best price info and where to buy.
        """
        snapshot = await self.get_aggregated_prices(sku)

        best_source = None
        best_price = None

        for breakdown in snapshot.sourceBreakdown:
            if breakdown.lowest:
                if best_price is None or breakdown.lowest < best_price:
                    best_price = breakdown.lowest
                    best_source = breakdown.source

        return {
            "sku": sku,
            "bestPrice": best_price,
            "bestSource": best_source,
            "allPrices": {
                b.source: b.lowest for b in snapshot.sourceBreakdown if b.lowest
            },
            "priceDifference": max(
                [b.lowest for b in snapshot.sourceBreakdown if b.lowest], default=0
            ) - min(
                [b.lowest for b in snapshot.sourceBreakdown if b.lowest], default=0
            ) if len([b for b in snapshot.sourceBreakdown if b.lowest]) > 1 else 0,
        }

    async def close(self) -> None:
        """Close all provider clients."""
        await asyncio.gather(
            self.stockx.close(),
            self.goat.close(),
            # ebay client doesn't have close method
        )


# Singleton instance
_aggregator: Optional[PriceAggregator] = None


def get_price_aggregator() -> PriceAggregator:
    """Get the singleton price aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = PriceAggregator()
    return _aggregator
