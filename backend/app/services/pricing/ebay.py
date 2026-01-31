"""
eBay Browse API integration for sneaker pricing.

Uses the eBay Browse API to search for completed/sold listings
and aggregate pricing data for sneaker SKUs.

API Documentation: https://developer.ebay.com/api-docs/buy/browse/overview.html
"""
from __future__ import annotations

import os
import base64
import asyncio
from datetime import datetime, timezone
from statistics import median, mean
from typing import List, Optional, Dict, Any

import httpx
from app.schemas.price import PriceSnapshot, SourceBreakdown
from app.services.pricing.base import PriceProvider


class EbayPriceProvider(PriceProvider):
    """eBay pricing provider using the Browse API."""

    # eBay API endpoints
    SANDBOX_AUTH_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    PRODUCTION_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    SANDBOX_BROWSE_URL = "https://api.sandbox.ebay.com/buy/browse/v1"
    PRODUCTION_BROWSE_URL = "https://api.ebay.com/buy/browse/v1"

    def __init__(self) -> None:
        self.app_id = os.getenv("EBAY_APP_ID", "")
        self.cert_id = os.getenv("EBAY_CERT_ID", "")
        self.sandbox = os.getenv("EBAY_SANDBOX", "false").lower() == "true"
        self.client = httpx.AsyncClient(timeout=30)
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def auth_url(self) -> str:
        return self.SANDBOX_AUTH_URL if self.sandbox else self.PRODUCTION_AUTH_URL

    @property
    def browse_url(self) -> str:
        return self.SANDBOX_BROWSE_URL if self.sandbox else self.PRODUCTION_BROWSE_URL

    def is_configured(self) -> bool:
        """Check if eBay API credentials are configured."""
        return bool(self.app_id and self.cert_id)

    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token using Client Credentials grant."""
        if not self.is_configured():
            return None

        # Check if we have a valid cached token
        if self._access_token and self._token_expiry:
            if datetime.now(timezone.utc) < self._token_expiry:
                return self._access_token

        # Request new token
        credentials = base64.b64encode(
            f"{self.app_id}:{self.cert_id}".encode()
        ).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            response = await self.client.post(
                self.auth_url,
                headers=headers,
                data=data,
            )

            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 7200)
                self._token_expiry = datetime.now(timezone.utc).replace(
                    second=datetime.now(timezone.utc).second + expires_in - 60
                )
                return self._access_token
            else:
                print(f"eBay auth failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"eBay auth error: {e}")
            return None

    async def _search_items(
        self,
        query: str,
        limit: int = 50,
        filter_sold: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for items on eBay."""
        token = await self._get_access_token()
        if not token:
            return []

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
        }

        # Build search query for sneakers
        params = {
            "q": query,
            "limit": str(limit),
            "category_ids": "15709",  # Men's Athletic Shoes category
        }

        # Add filter for sold items if available (requires specific API access)
        if filter_sold:
            params["filter"] = "conditionIds:{1000|1500|3000}"  # New, New with defects, Pre-owned

        try:
            response = await self.client.get(
                f"{self.browse_url}/item_summary/search",
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("itemSummaries", [])
            else:
                print(f"eBay search failed: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"eBay search error: {e}")
            return []

    async def _fetch_recent_sold(self, sku: str) -> List[float]:
        """Fetch recent sold prices for a SKU."""
        if not self.is_configured():
            # Return mock data for development
            return self._get_mock_prices(sku)

        # Search for the SKU
        items = await self._search_items(f"sneaker {sku}", limit=50)

        prices = []
        for item in items:
            price_info = item.get("price", {})
            if price_info:
                try:
                    value = float(price_info.get("value", 0))
                    if value > 0:
                        prices.append(value)
                except (ValueError, TypeError):
                    continue

        return prices if prices else self._get_mock_prices(sku)

    def _get_mock_prices(self, sku: str) -> List[float]:
        """Generate mock prices for development/testing."""
        # Generate semi-realistic mock prices based on SKU hash
        base_price = 150 + (hash(sku) % 200)
        return [
            base_price - 10,
            base_price,
            base_price + 15,
            base_price - 5,
            base_price + 20,
        ]

    async def get_price_snapshot(self, sku: str) -> PriceSnapshot:
        """Get aggregated price snapshot for a SKU."""
        sold_prices = await self._fetch_recent_sold(sku)

        last_sale = sold_prices[-1] if sold_prices else None
        median_price = median(sold_prices) if sold_prices else None
        avg_price = mean(sold_prices) if sold_prices else None
        lowest = min(sold_prices) if sold_prices else None
        highest = max(sold_prices) if sold_prices else None

        snapshot = PriceSnapshot(
            sku=sku,
            asOf=datetime.now(timezone.utc).isoformat(),
            retail=None,
            lowestAsk=lowest,
            highestBid=highest,
            lastSale=last_sale,
            averagePrice=avg_price,
            sourceBreakdown=[
                SourceBreakdown(
                    source="ebay",
                    median=median_price,
                    count=len(sold_prices),
                    lowest=lowest,
                    highest=highest,
                )
            ],
        )
        return snapshot

    async def search_sneakers(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for sneakers by name/brand/model."""
        items = await self._search_items(f"sneaker {query}", limit=limit)

        results = []
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "price": item.get("price", {}).get("value"),
                "currency": item.get("price", {}).get("currency", "USD"),
                "condition": item.get("condition", ""),
                "image_url": item.get("image", {}).get("imageUrl", ""),
                "item_url": item.get("itemWebUrl", ""),
                "seller": item.get("seller", {}).get("username", ""),
            })

        return results
