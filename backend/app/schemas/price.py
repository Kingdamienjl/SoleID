from pydantic import BaseModel
from typing import List, Optional


class SourceBreakdown(BaseModel):
    source: str
    median: Optional[float] = None
    count: Optional[int] = None


class PriceSnapshot(BaseModel):
    sku: str
    asOf: str
    retail: Optional[float] = None
    lowestAsk: Optional[float] = None
    lastSale: Optional[float] = None
    sourceBreakdown: List[SourceBreakdown] = []
