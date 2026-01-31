"""
Image validation endpoint for pre-flight checks before matching.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas.validation import ValidationResult, ValidationResponse
from app.services.validation import get_validation_service
from PIL import Image
import io

router = APIRouter()


@router.post("/validate", response_model=ValidationResponse)
async def validate_endpoint(image: UploadFile = File(...)) -> ValidationResponse:
    """
    Validate an image before matching.

    Returns validation result indicating if the image:
    - Contains a shoe/sneaker (CLIP classification)
    - Has acceptable quality (not blurry, proper lighting)

    This is a lightweight pre-flight check that can be called before
    the full /match endpoint to provide faster feedback to users.

    - **image**: Image file to validate (JPEG, PNG)
    """
    # Parse image
    try:
        content = await image.read()
        pil = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

    # Run validation
    validation_service = get_validation_service()
    validation_result = await validation_service.validate_image(pil)

    return ValidationResponse(validation=validation_result)
