from pydantic import BaseModel
from typing import List, Optional


class SourceBreakdown(BaseModel):
    source: str
    median: Optional[float] = None
    count: Optional[int] = None
    lowest: Optional[float] = None
    highest: Optional[float] = None
    buyUrl: Optional[str] = None  # direct product/listing page on this source; None when data is mocked


class PriceSnapshot(BaseModel):
    sku: str
    asOf: str
    retail: Optional[float] = None
    lowestAsk: Optional[float] = None
    highestBid: Optional[float] = None
    lastSale: Optional[float] = None
    averagePrice: Optional[float] = None
    sourceBreakdown: List[SourceBreakdown] = []
