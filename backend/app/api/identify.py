import io
import os

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


def _enabled() -> bool:
    return os.getenv("IDENTIFY_ENABLED", "").lower() in ("1", "true", "yes")


@router.post("/identify", response_model=IdentifyResponse)
async def identify_endpoint(
    image: UploadFile = File(...),
    user: FirebaseUser = Depends(get_current_user),
) -> IdentifyResponse:
    """
    Identify a shoe from a photo using the vision-first pipeline.

    Disabled unless IDENTIFY_ENABLED=1 — the eval gate in the pivot spec
    decides when this replaces /match.
    """
    if not _enabled():
        raise HTTPException(
            status_code=503,
            detail="identify endpoint is disabled (set IDENTIFY_ENABLED=1)",
        )

    content = await image.read()
    try:
        Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

    mime_type = image.content_type or "image/jpeg"
    try:
        return await identify_shoe(content, mime_type)
    except NotAShoeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BudgetExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except NoProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
