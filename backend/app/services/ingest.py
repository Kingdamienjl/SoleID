from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List

import numpy as np
from PIL import Image
import imagehash

from app.schemas.shoe import Shoe
from app.services.embedding import get_embedding_service, preprocess_image_for_openclip
from app.services.vector import get_vector_service


def compute_phash(image: Image.Image) -> str:
    return str(imagehash.phash(image))


@dataclass
class CanonicalImage:
    file_id: str
    phash: str


async def upsert_shoes(shoes: List[Shoe], image_loader) -> None:
    """
    Upserts a list of shoes into Qdrant with deduped canonical images.
    image_loader: callable that takes drive file id and returns PIL.Image
    """

    embedding = get_embedding_service()
    vector = get_vector_service()

    ids: List[str] = []
    vectors: List[np.ndarray] = []
    payloads: List[dict] = []

    for shoe in shoes:
        seen_hashes: set[str] = set()
        kept_images: List[str] = []
        for fid in shoe.images:
            try:
                img = image_loader(fid)
                h = compute_phash(img)
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                kept_images.append(fid)
                # Embed this image; we use first N=6
                tensor = preprocess_image_for_openclip(img)
                vec = await embedding.embed_tensor(tensor)
                ids.append(f"{shoe.id}:{fid}")
                vectors.append(vec)
                payloads.append(shoe.model_copy(update={"images": kept_images}).model_dump())
                if len(kept_images) >= 6:
                    break
            except Exception:
                continue

    if ids:
        await vector.upsert(ids=ids, vectors=np.stack(vectors, axis=0), payloads=payloads)
