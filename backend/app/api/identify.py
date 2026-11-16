import io
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

from app.dependencies.auth import get_current_user
from app.schemas.identify import IdentifyResponse
from app.services.auth import FirebaseUser
from app.services.identify import (
    NoProviderError,
    NotAShoeError,
    identify_shoe,
)
from app.services.vision.budget import BudgetExceeded

router = APIRouter()

MAX_IMAGES = 3


def _enabled() -> bool:
    return os.getenv("IDENTIFY_ENABLED", "").lower() in ("1", "true", "yes")


@router.post("/identify", response_model=IdentifyResponse)
async def identify_endpoint(
    image: Optional[UploadFile] = File(default=None),
    images: Optional[List[UploadFile]] = File(default=None),
    user: FirebaseUser = Depends(get_current_user),
) -> IdentifyResponse:
    """
    Identify a shoe from one or more photos using the vision-first pipeline.

    Send a single photo as `image` (legacy) or 1-3 photos as repeated
    `images` parts. When one photo fails to identify the shoe confidently,
    the response sets needsSecondPhoto and the client must prompt for a
    second photo (different angle) and resubmit with both photos.

    Disabled unless IDENTIFY_ENABLED=1 — the eval gate in the pivot spec
    decides when this replaces /match.
    """
    if not _enabled():
        raise HTTPException(
            status_code=503,
            detail="identify endpoint is disabled (set IDENTIFY_ENABLED=1)",
        )

    uploads: List[UploadFile] = (
        list(images) if images else ([image] if image is not None else [])
    )
    if not uploads:
        raise HTTPException(
            status_code=400,
            detail="no image uploaded (send `image` or `images`)",
        )
    if len(uploads) > MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"at most {MAX_IMAGES} photos per identify request",
        )

    decoded: List[tuple[bytes, str]] = []
    for upload in uploads:
        content = await upload.read()
        try:
            Image.open(io.BytesIO(content)).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc
        decoded.append((content, upload.content_type or "image/jpeg"))

    try:
        return await identify_shoe(decoded)
    except NotAShoeError as exc:
        # One photo that shows no shoe: ask for a second angle instead of
        # hard-failing — the shoe may be out of frame. With 2+ photos the
        # user already tried, so keep the 400.
        if len(decoded) == 1:
            return IdentifyResponse(
                confidence=0.0,
                source="vision",
                needsSecondPhoto=True,
                secondPhotoReason="not_a_shoe",
            )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BudgetExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except NoProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
