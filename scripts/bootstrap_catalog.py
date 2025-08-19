#!/usr/bin/env python3
"""
Seed demo shoes (50 items) with mock Drive IDs and upsert vectors.
"""
import asyncio
import uuid
from typing import List
from PIL import Image

from app.schemas.shoe import Shoe, SourceRef
from app.services.ingest import upsert_shoes


def _make_demo_shoes(n: int = 50) -> List[Shoe]:
    shoes = []
    for i in range(n):
        sku = f"555088-{100 + i}"
        shoes.append(
            Shoe(
                id=str(uuid.uuid4()),
                brand="Nike",
                model="Air Jordan 1 Retro High",
                colorway=f"Demo Colorway {i}",
                sku=sku,
                year=2021,
                aliases=["AJ1", "Jordan 1"],
                images=[f"drive://demo_image_{i}_1", f"drive://demo_image_{i}_2"],
                sources=[SourceRef(name="ebay", url="https://www.ebay.com")],
                lastPriceSnapshotAt=None,
            )
        )
    return shoes


def _fake_image_loader(file_id: str) -> Image.Image:
    # Produce a simple generated image based on file_id hash
    h = abs(hash(file_id)) % 255
    img = Image.new("RGB", (400, 400), color=(h, 255 - h, (h * 2) % 255))
    return img


async def _main():
    shoes = _make_demo_shoes(50)
    await upsert_shoes(shoes, image_loader=_fake_image_loader)
    print("Seeded demo shoes and upserted vectors (mock images)")


if __name__ == "__main__":
    asyncio.run(_main())
