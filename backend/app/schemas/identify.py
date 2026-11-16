from typing import List, Optional

from pydantic import BaseModel

from app.schemas.price import PriceSnapshot
from app.services.vision.base import ShoeCandidate


class IdentifyResponse(BaseModel):
    """Result of POST /identify.

    Three shapes:
    - shoe set: a confident identification (candidates holds any alternates)
    - shoe null, needsSecondPhoto false: low confidence or unverifiable SKU —
      the client should let the user pick from candidates (candidates[0] is
      the primary guess)
    - needsSecondPhoto true: the single photo did not identify the shoe
      confidently; the client must prompt for a second photo (different
      angle) and resubmit with both photos. secondPhotoReason says why:
      low_confidence | not_a_shoe | unverified_sku.
    """

    shoe: Optional[ShoeCandidate] = None
    candidates: List[ShoeCandidate] = []
    confidence: float = 0.0
    source: str = "vision"  # vision | cache | qdrant_cache
    skuVerified: bool = False  # styleId resolved to a real live listing
    prices: Optional[PriceSnapshot] = None
    needsSecondPhoto: bool = False
    secondPhotoReason: Optional[str] = None
