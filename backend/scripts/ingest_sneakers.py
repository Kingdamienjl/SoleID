#!/usr/bin/env python3
"""
Sneaker Data Ingestion Script
Reads sneakers from the scraper SQLite database and ingests them into Qdrant.
Supports both remote image URLs (from Sneaks-API) and local image files.
"""

import os
import sys
import asyncio
import hashlib
import io
from pathlib import Path
from typing import Optional, List, Dict, Any
import sqlite3
from PIL import Image
import numpy as np

# Add parent to path for imports
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Load .env from backend directory
_env_file = BACKEND_DIR / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value

from app.services.embedding import get_embedding_service, preprocess_image_for_openclip
from app.services.vector import get_vector_service

# Paths
SCRAPER_DB = Path(__file__).parent.parent.parent / "sneaker-scraper" / "sneakers.db"
SCRAPER_DATA = Path(__file__).parent.parent.parent / "sneaker-scraper" / "data"

# Image cache directory (to avoid re-downloading)
IMAGE_CACHE = SCRAPER_DATA / "image_cache"


def get_db_connection():
    """Connect to the scraper SQLite database."""
    if not SCRAPER_DB.exists():
        raise FileNotFoundError(f"Database not found: {SCRAPER_DB}")
    return sqlite3.connect(str(SCRAPER_DB))


def get_sneakers_with_images(conn, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch sneakers that have associated image URLs."""
    cursor = conn.cursor()

    # Only fetch sneakers that have at least one image
    query = """
        SELECT
            s.id, s.name, s.brand, s.model, s.colorway, s.sku,
            s.retail_price, s.release_date, s.description,
            si.image_url, si.image_type
        FROM sneakers s
        INNER JOIN sneaker_images si ON s.id = si.sneaker_id
        WHERE si.image_url IS NOT NULL AND si.image_url != ''
        ORDER BY s.id
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    # Group by sneaker
    sneakers = {}
    for row in rows:
        sid = row[0]
        if sid not in sneakers:
            sneakers[sid] = {
                "id": row[0],
                "name": row[1],
                "brand": row[2],
                "model": row[3],
                "colorway": row[4],
                "sku": row[5],
                "retail_price": row[6],
                "release_date": str(row[7]) if row[7] else None,
                "description": row[8],
                "images": []
            }
        sneakers[sid]["images"].append({
            "url": row[9],
            "type": row[10]
        })

    result = list(sneakers.values())
    if limit:
        result = result[:limit]
    return result


def generate_point_id(sneaker_id: int, image_url: str) -> str:
    """Generate a unique ID for a Qdrant point."""
    hash_input = f"{sneaker_id}:{image_url}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def get_cache_path(url: str) -> Path:
    """Get local cache path for a URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = ".jpg"
    if ".png" in url.lower():
        ext = ".png"
    return IMAGE_CACHE / f"{url_hash}{ext}"


async def download_image(session, url: str) -> Optional[Image.Image]:
    """Download an image from URL, using cache if available."""
    cache_path = get_cache_path(url)

    # Check cache first
    if cache_path.exists():
        try:
            return Image.open(cache_path).convert("RGB")
        except Exception:
            cache_path.unlink(missing_ok=True)

    # Download
    try:
        resp = await asyncio.to_thread(session.get, url, timeout=15)
        if resp.status_code != 200:
            return None
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        # Cache locally
        IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
        img.save(str(cache_path), quality=85)
        return img
    except Exception:
        return None


async def embed_pil_image(img: Image.Image) -> Optional[np.ndarray]:
    """Generate embedding for a PIL Image."""
    try:
        embedding_service = get_embedding_service()
        tensor = preprocess_image_for_openclip(img)
        embedding = await embedding_service.embed_tensor(tensor)
        return embedding
    except Exception as e:
        print(f"  Error embedding image: {e}")
        return None


async def ingest_sneakers(
    limit: Optional[int] = None,
    batch_size: int = 50,
    max_images_per_shoe: int = 3,
    source: str = "all",
):
    """
    Main ingestion function.

    Args:
        limit: Max number of sneakers to process
        batch_size: How many vectors to upsert at once
        max_images_per_shoe: Max images to embed per sneaker (saves time/space)
        source: 'remote' for DB URLs only, 'local' for files only, 'all' for both
    """
    import requests

    print("=" * 60)
    print("SoleID Sneaker Data Ingestion -> Qdrant Cloud")
    print("=" * 60)

    # Check database
    print(f"\n1. Checking database: {SCRAPER_DB}")
    if not SCRAPER_DB.exists():
        print("   ERROR: Database not found!")
        return
    print("   Database found.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM sneakers")
    total_sneakers = cursor.fetchone()[0]
    print(f"   Total sneakers in DB: {total_sneakers}")

    cursor.execute("SELECT COUNT(*) FROM sneaker_images WHERE image_url LIKE 'http%'")
    total_remote = cursor.fetchone()[0]
    print(f"   Remote image URLs: {total_remote}")

    # Initialize services
    print(f"\n2. Initializing services...")
    embedding_service = get_embedding_service()
    vector_service = get_vector_service()
    print(f"   Embedding: {'MOCK MODE' if embedding_service.mock else 'OpenCLIP ViT-B-16'}")
    print(f"   Qdrant collection: '{vector_service.collection}'")

    # Check existing collection size
    try:
        info = vector_service.client.get_collection(vector_service.collection)
        existing_points = info.points_count
        print(f"   Existing vectors in collection: {existing_points}")
    except Exception:
        existing_points = 0
        print("   Collection will be created on first upsert")

    # Fetch sneakers with images from DB
    print(f"\n3. Fetching sneakers with images...")
    sneakers = get_sneakers_with_images(conn, limit=limit)
    print(f"   Found {len(sneakers)} sneakers with image URLs")

    if not sneakers:
        print("   Nothing to ingest!")
        conn.close()
        return

    # Process
    print(f"\n4. Downloading images, generating embeddings, upserting to Qdrant...")
    print(f"   Max {max_images_per_shoe} image(s) per sneaker, batch size {batch_size}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "SoleID/1.0 (Sneaker Identification App)"
    })

    processed_sneakers = 0
    processed_images = 0
    failed_downloads = 0
    failed_embeddings = 0
    skipped = 0

    batch_ids = []
    batch_vectors = []
    batch_payloads = []

    for i, sneaker in enumerate(sneakers):
        brand = sneaker.get("brand") or "Unknown"
        model = sneaker.get("model") or sneaker.get("name") or "Unknown"
        colorway = sneaker.get("colorway") or ""
        sku = sneaker.get("sku") or ""
        sneaker_id = sneaker["id"]

        # Build Shoe-compatible payload
        image_urls = [img["url"] for img in sneaker["images"]]
        payload = {
            "id": str(sneaker_id),
            "brand": brand,
            "model": model,
            "colorway": colorway,
            "sku": sku,
            "year": None,
            "aliases": [],
            "images": image_urls[:max_images_per_shoe],
            "sources": [{"name": "sneaks-api", "url": url} for url in image_urls[:max_images_per_shoe]],
            "lastPriceSnapshotAt": None,
        }

        # Process up to max_images_per_shoe images
        shoe_embedded = False
        for img_info in sneaker["images"][:max_images_per_shoe]:
            url = img_info["url"]

            if not url.startswith("http"):
                skipped += 1
                continue

            # Download
            img = await download_image(session, url)
            if img is None:
                failed_downloads += 1
                continue

            # Embed
            embedding = await embed_pil_image(img)
            if embedding is None:
                failed_embeddings += 1
                continue

            # Add to batch
            point_id = generate_point_id(sneaker_id, url)
            batch_ids.append(point_id)
            batch_vectors.append(embedding)
            batch_payloads.append(payload)
            processed_images += 1
            shoe_embedded = True

        if shoe_embedded:
            processed_sneakers += 1

        # Upsert batch when full
        if len(batch_ids) >= batch_size:
            print(f"   Upserting batch of {len(batch_ids)} vectors...")
            await vector_service.upsert(
                ids=batch_ids,
                vectors=np.array(batch_vectors),
                payloads=batch_payloads
            )
            batch_ids = []
            batch_vectors = []
            batch_payloads = []

        # Progress every 100 sneakers
        if (i + 1) % 100 == 0:
            print(
                f"   Progress: {i + 1}/{len(sneakers)} sneakers "
                f"({processed_images} images embedded, "
                f"{failed_downloads} download fails, "
                f"{failed_embeddings} embed fails)"
            )

    # Final batch
    if batch_ids:
        print(f"   Upserting final batch of {len(batch_ids)} vectors...")
        await vector_service.upsert(
            ids=batch_ids,
            vectors=np.array(batch_vectors),
            payloads=batch_payloads
        )

    # Final stats
    print(f"\n5. Ingestion complete!")
    print(f"   Sneakers processed: {processed_sneakers}/{len(sneakers)}")
    print(f"   Images embedded:    {processed_images}")
    print(f"   Download failures:  {failed_downloads}")
    print(f"   Embedding failures: {failed_embeddings}")
    print(f"   Skipped (non-URL):  {skipped}")

    # Verify collection
    try:
        info = vector_service.client.get_collection(vector_service.collection)
        print(f"   Qdrant collection '{vector_service.collection}': {info.points_count} total vectors")
    except Exception as e:
        print(f"   Could not verify collection: {e}")

    print("=" * 60)
    conn.close()
    session.close()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest sneaker data into Qdrant")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of sneakers to process")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for upserts")
    parser.add_argument("--max-images", type=int, default=3, help="Max images per sneaker")
    args = parser.parse_args()

    await ingest_sneakers(
        limit=args.limit,
        batch_size=args.batch_size,
        max_images_per_shoe=args.max_images,
    )


if __name__ == "__main__":
    asyncio.run(main())
