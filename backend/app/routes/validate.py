from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import io

from app.schemas.validation import ValidationResult
from app.services.validation import get_validation_service

router = APIRouter()


@router.post("/validate", response_model=ValidationResult)
async def validate_endpoint(
    image: UploadFile = File(...),
) -> ValidationResult:
    """
    Validate an image for sneaker matching without performing the match.

    Use this endpoint for quick pre-flight checks before sending to /match.

    - **image**: Image file to validate (JPEG, PNG)

    Returns validation result with:
    - is_valid: Whether image passes all checks
    - confidence: CLIP shoe detection confidence (0-1)
    - validation_errors: List of issues found
    - suggestions: Helpful tips to fix issues
    """
    # Parse image
    try:
        content = await image.read()
        pil = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

    # Run validation
    validation_service = get_validation_service()
    result = await validation_service.validate_image(pil)

    return result
