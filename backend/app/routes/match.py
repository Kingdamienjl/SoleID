from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from app.schemas.match import MatchResponse, Candidate
from app.services.embedding import get_embedding_service
from app.services.vector import get_vector_service
from app.services.embedding import preprocess_image_for_openclip
from PIL import Image
import io

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
async def match_endpoint(image: UploadFile = File(...), top_k: int = 5) -> MatchResponse:
    try:
        content = await image.read()
        pil = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

    tensor = preprocess_image_for_openclip(pil)
    embedding_service = get_embedding_service()
    vector = await embedding_service.embed_tensor(tensor)

    vector_service = get_vector_service()
    results = await vector_service.query(vector, top_k=top_k)

    candidates: List[Candidate] = []
    for item in results:
        candidates.append(
            Candidate(score=item.score, shoe=item.payload),
        )

    return MatchResponse(candidates=candidates)
