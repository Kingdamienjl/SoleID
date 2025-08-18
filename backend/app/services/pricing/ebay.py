from __future__ import annotations

import os
from statistics import median
from typing import List

import httpx
from app.schemas.price import PriceSnapshot, SourceBreakdown
from app.services.pricing.base import PriceProvider


class EbayPriceProvider(PriceProvider):
    def __init__(self) -> None:
        self.app_id = os.getenv("EBAY_APP_ID", "")
        self.client = httpx.AsyncClient(timeout=15)

    async def _fetch_recent_sold(self, sku: str) -> List[float]:
        # Minimal viable use of eBay Finding API equivalent; when APP_ID missing, return mock
        if not self.app_id:
            # Mock data for dev/test
            return [360.0, 370.0, 355.0, 365.0]
        # Placeholder: real implementation would call eBay APIs
        return [360.0, 370.0, 355.0, 365.0]

    async def get_price_snapshot(self, sku: str) -> PriceSnapshot:
        sold = await self._fetch_recent_sold(sku)
        last_sale = sold[-1] if sold else None
        med = median(sold) if sold else None
        snapshot = PriceSnapshot(
            sku=sku,
            asOf="",
            retail=None,
            lowestAsk=None,
            lastSale=last_sale,
            sourceBreakdown=[SourceBreakdown(source="ebay", median=med, count=len(sold))],
        )
        return snapshot
