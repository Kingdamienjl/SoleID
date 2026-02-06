"""
Price provider services for sneaker marketplaces.

Available providers:
- StockXPriceProvider: Real-time market data from StockX
- GoatPriceProvider: New and used prices from GOAT
- EbayPriceProvider: Sold listing prices from eBay
- PriceAggregator: Combines all providers for comprehensive data

Usage:
    from app.services.pricing import get_price_aggregator

    aggregator = get_price_aggregator()
    snapshot = await aggregator.get_aggregated_prices("DD1391-100")
"""
from app.services.pricing.base import PriceProvider
from app.services.pricing.stockx import StockXPriceProvider
from app.services.pricing.goat import GoatPriceProvider
from app.services.pricing.ebay import EbayPriceProvider
from app.services.pricing.aggregator import PriceAggregator, get_price_aggregator

__all__ = [
    "PriceProvider",
    "StockXPriceProvider",
    "GoatPriceProvider",
    "EbayPriceProvider",
    "PriceAggregator",
    "get_price_aggregator",
]
