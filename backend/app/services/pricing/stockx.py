from __future__ import annotations

import os
from app.schemas.price import PriceSnapshot
from app.services.pricing.base import PriceProvider


class StockXPriceProvider(PriceProvider):
    def __init__(self) -> None:
        self.enabled = os.getenv("ENABLE_UNOFFICIAL_STOCKX", "false").lower() == "true"

    async def get_price_snapshot(self, sku: str) -> PriceSnapshot:
        if not self.enabled:
            return PriceSnapshot(sku=sku, asOf="", retail=None, lowestAsk=None, lastSale=None, sourceBreakdown=[])
        # Placeholder for disabled-by-default scraper
        return PriceSnapshot(sku=sku, asOf="", retail=None, lowestAsk=None, lastSale=None, sourceBreakdown=[])
