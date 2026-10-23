from typing import List, Optional

from pydantic import BaseModel

from app.schemas.price import PriceSnapshot
from app.services.vision.base import ShoeCandidate


class IdentifyResponse(BaseModel):
    """Result of POST /identify.

    Exactly one of two shapes:
    - shoe set: a confident identification (candidates holds any alternates)
    - shoe null: low confidence or unverifiable SKU — the client should let
      the user pick from candidates (primary guess is candidates[0])
    """

    shoe: Optional[ShoeCandidate] = None
    candidates: List[ShoeCandidate] = []
    confidence: float = 0.0
    source: str = "vision"  # vision | cache | qdrant_cache
    skuVerified: bool = False  # styleId resolved to a real live listing
    prices: Optional[PriceSnapshot] = None
