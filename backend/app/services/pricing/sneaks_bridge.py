"""
Bridge to the Sneaks-API Node.js microservice.

Provides async Python access to real-time sneaker data from StockX and GOAT
via the sneaks-service running on localhost:3001.

Environment Variables:
- SNEAKS_SERVICE_URL: Base URL (default: http://localhost:3001)
"""
from __future__ import annotations

import os
import logging
from typing import List, Optional, Dict, Any

import httpx

logger = logging.getLogger("soleid.pricing.sneaks_bridge")

SNEAKS_SERVICE_URL = os.getenv("SNEAKS_SERVICE_URL", "http://localhost:3001")


class SneaksBridge:
    """Async HTTP client for the sneaks-service Node.js microservice."""

    def __init__(self, base_url: str = SNEAKS_SERVICE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=35)
        self._available: Optional[bool] = None
        logger.info("SneaksBridge initialized (url=%s)", self.base_url)

    async def health_check(self) -> bool:
        """Check if the sneaks-service is running."""
        try:
            resp = await self.client.get(f"{self.base_url}/health", timeout=5)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available

    @property
    def is_available(self) -> Optional[bool]:
        """Last known availability status (None if never checked)."""
        return self._available

    async def search(self, keyword: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Search for sneakers by keyword.

        Returns list of product dicts or None on failure.
        Each product has: name, brand, colorway, styleID, retailPrice,
        thumbnail, lowestResellPrice, resellLinks, etc.
        """
        try:
            resp = await self.client.get(
                f"{self.base_url}/search",
                params={"q": keyword, "limit": limit},
            )
            if resp.status_code == 200:
                data = resp.json()
                self._available = True
                return data.get("products", [])
            else:
                logger.warning("Sneaks search failed: HTTP %s", resp.status_code)
        except httpx.ConnectError:
            logger.warning("Sneaks service not reachable at %s", self.base_url)
            self._available = False
        except Exception as e:
            logger.error("Sneaks search error: %s", e)
        return None

    async def get_prices(self, style_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full product data with pricing for a style ID.

        Returns product dict with: name, brand, retailPrice, styleID,
        resellPrices (StockX by size), goatPrices (GOAT by size),
        lowestResellPrice, images, resellLinks.
        """
        try:
            resp = await self.client.get(
                f"{self.base_url}/prices/{style_id}",
            )
            if resp.status_code == 200:
                self._available = True
                return resp.json()
            elif resp.status_code == 404:
                logger.debug("Product not found in sneaks-service: %s", style_id)
                return None
            else:
                logger.warning("Sneaks price lookup failed: HTTP %s", resp.status_code)
        except httpx.ConnectError:
            logger.warning("Sneaks service not reachable at %s", self.base_url)
            self._available = False
        except Exception as e:
            logger.error("Sneaks price lookup error: %s", e)
        return None

    async def get_trending(self, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        Get trending/most popular sneakers.

        Returns list of product dicts or None on failure.
        """
        try:
            resp = await self.client.get(
                f"{self.base_url}/trending",
                params={"limit": limit},
            )
            if resp.status_code == 200:
                data = resp.json()
                self._available = True
                return data.get("products", [])
            else:
                logger.warning("Sneaks trending failed: HTTP %s", resp.status_code)
        except httpx.ConnectError:
            logger.warning("Sneaks service not reachable at %s", self.base_url)
            self._available = False
        except Exception as e:
            logger.error("Sneaks trending error: %s", e)
        return None

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_bridge: Optional[SneaksBridge] = None


def get_sneaks_bridge() -> SneaksBridge:
    """Get the singleton SneaksBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = SneaksBridge()
    return _bridge
