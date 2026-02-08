from pydantic import BaseModel, Field
from typing import List, Optional


class SourceRef(BaseModel):
    name: str
    url: str


class Shoe(BaseModel):
    id: str
    brand: str
    model: str
    colorway: str
    sku: str
    year: Optional[int] = None
    aliases: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    sources: List[SourceRef] = Field(default_factory=list)
    lastPriceSnapshotAt: Optional[str] = None
    retail_price: Optional[float] = None
    description: str = ""
    release_date: str = ""
    resell_prices: Optional[dict] = None
