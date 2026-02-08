from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from typing import List, Optional

from app.dependencies.auth import get_current_user
from app.services.auth import FirebaseUser
from app.services.embedding import get_embedding_service
from app.services.vector import get_vector_service
from app.services.validation import get_validation_service
from app.services.embedding import preprocess_image_for_openclip
from app.routes.search import _shoe_to_sneaker
from PIL import Image
import io

router = APIRouter()


@router.post("/match")
async def match_endpoint(
    image: UploadFile = File(...),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of candidates to return"),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold"),
    skip_validation: bool = Query(default=False, description="Skip shoe detection validation"),
    user: FirebaseUser = Depends(get_current_user),
) -> dict:
    """
    Match an uploaded image against the sneaker database.

    - **image**: Image file to match (JPEG, PNG)
    - **top_k**: Maximum number of match candidates to return (default: 5)
    - **min_score**: Filter out matches below this similarity threshold (default: 0.0)
    - **skip_validation**: Skip CLIP-based shoe validation (default: False)
    """
    # Parse image
    try:
        content = await image.read()
        pil = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

    # Validate image contains a shoe (unless skipped)
    if not skip_validation:
        validation_service = get_validation_service()
        validation_result = await validation_service.validate_image(pil)

        if not validation_result.is_valid:
            # Return 400 with validation details
            error_detail = {
                "message": "Image validation failed",
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "confidence": validation_result.confidence,
                    "errors": validation_result.validation_errors,
                    "suggestions": validation_result.suggestions,
                }
            }
            raise HTTPException(status_code=400, detail=error_detail)

    # Generate embedding
    tensor = preprocess_image_for_openclip(pil)
    embedding_service = get_embedding_service()
    vector = await embedding_service.embed_tensor(tensor)

    # Query vector database
    vector_service = get_vector_service()
    results = await vector_service.query(vector, top_k=top_k)

    # Filter by min_score and build response with Android-compatible sneaker format
    candidates = []
    for item in results:
        if item.score >= min_score:
            sneaker_out = _shoe_to_sneaker(item.payload)
            candidates.append({
                "score": item.score,
                "shoe": sneaker_out.model_dump(),
            })

    return {"candidates": candidates}
