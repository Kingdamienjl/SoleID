from __future__ import annotations

from abc import ABC, abstractmethod
from app.schemas.price import PriceSnapshot


class PriceProvider(ABC):
    @abstractmethod
    async def get_price_snapshot(self, sku: str) -> PriceSnapshot:  # pragma: no cover - interface
        raise NotImplementedError
