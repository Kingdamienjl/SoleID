#!/usr/bin/env python3
"""
Sneaker Data Ingestion Script
Reads sneakers from the scraper SQLite database and ingests them into Qdrant.
"""

import os
import sys
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
import sqlite3
from PIL import Image
import numpy as np

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.embedding import get_embedding_service, preprocess_image_for_openclip
from app.services.vector import get_vector_service

# Paths
SCRAPER_DB = Path(__file__).parent.parent.parent / "sneaker-scraper" / "sneakers.db"
SCRAPER_DATA = Path(__file__).parent.parent.parent / "sneaker-scraper" / "data"

# Image directories to search
IMAGE_DIRS = [
    "real_sneaker_images",
    "enhanced_sneaker_images",
    "enhanced_images",
    "comprehensive_images",
    "api_images",
    "direct_images",
    "images",
]


def get_db_connection():
    """Connect to the scraper SQLite database."""
    if not SCRAPER_DB.exists():
        raise FileNotFoundError(f"Database not found: {SCRAPER_DB}")
    return sqlite3.connect(str(SCRAPER_DB))


def get_sneakers_with_images(conn, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch sneakers that have associated images."""
    cursor = conn.cursor()

    query = """
        SELECT
            s.id, s.name, s.brand, s.model, s.colorway, s.sku,
            s.retail_price, s.release_date, s.description,
            si.image_url, si.google_drive_id, si.image_type
        FROM sneakers s
        LEFT JOIN sneaker_images si ON s.id = si.sneaker_id
        ORDER BY s.id
    """
    if limit:
        query += f" LIMIT {limit}"

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
        if row[9]:  # image_url
            sneakers[sid]["images"].append({
                "url": row[9],
                "drive_id": row[10],
                "type": row[11]
            })

    return list(sneakers.values())


def find_local_image(sneaker: Dict[str, Any]) -> Optional[Path]:
    """Try to find a local image file for the sneaker."""
    # Check each image directory
    for img_dir in IMAGE_DIRS:
        dir_path = SCRAPER_DATA / img_dir
        if not dir_path.exists():
            continue

        # Search for images matching sneaker name/brand/sku
        search_terms = []
        if sneaker.get("sku"):
            search_terms.append(sneaker["sku"].lower().replace("-", "").replace(" ", ""))
        if sneaker.get("brand"):
            search_terms.append(sneaker["brand"].lower())
        if sneaker.get("model"):
            search_terms.append(sneaker["model"].lower().replace(" ", "_"))

        for img_file in dir_path.glob("*.jpg"):
            filename = img_file.stem.lower()
            for term in search_terms:
                if term and term in filename:
                    return img_file

        for img_file in dir_path.glob("*.png"):
            filename = img_file.stem.lower()
            for term in search_terms:
                if term and term in filename:
                    return img_file

    return None


def get_all_local_images() -> List[Path]:
    """Get all local images from the data directories."""
    images = []
    for img_dir in IMAGE_DIRS:
        dir_path = SCRAPER_DATA / img_dir
        if dir_path.exists():
            images.extend(dir_path.glob("*.jpg"))
            images.extend(dir_path.glob("*.png"))
            images.extend(dir_path.glob("*.jpeg"))
    return images


def generate_point_id(sneaker_id: int, image_path: str) -> str:
    """Generate a unique ID for a Qdrant point."""
    hash_input = f"{sneaker_id}:{image_path}"
    return hashlib.md5(hash_input.encode()).hexdigest()


async def embed_image(image_path: Path) -> Optional[np.ndarray]:
    """Generate embedding for an image file."""
    try:
        embedding_service = get_embedding_service()
        img = Image.open(image_path).convert("RGB")
        tensor = preprocess_image_for_openclip(img)
        embedding = await embedding_service.embed_tensor(tensor)
        return embedding
    except Exception as e:
        print(f"  Error embedding {image_path}: {e}")
        return None


async def ingest_sneakers(limit: Optional[int] = None, batch_size: int = 50):
    """Main ingestion function."""
    print("=" * 60)
    print("SoleID Sneaker Data Ingestion")
    print("=" * 60)

    # Check database
    print(f"\n1. Checking database: {SCRAPER_DB}")
    if not SCRAPER_DB.exists():
        print(f"   ERROR: Database not found!")
        return
    print("   Database found.")

    # Connect and get stats
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM sneakers")
    total_sneakers = cursor.fetchone()[0]
    print(f"   Total sneakers in DB: {total_sneakers}")

    cursor.execute("SELECT COUNT(*) FROM sneaker_images")
    total_images = cursor.fetchone()[0]
    print(f"   Total images in DB: {total_images}")

    # Get local images
    print(f"\n2. Scanning local image directories...")
    local_images = get_all_local_images()
    print(f"   Found {len(local_images)} local image files")

    # Initialize services
    print(f"\n3. Initializing services...")
    embedding_service = get_embedding_service()
    vector_service = get_vector_service()
    print(f"   Embedding service: {'MOCK MODE' if embedding_service.mock else 'OpenCLIP ViT-B-16'}")
    print(f"   Vector service: Qdrant collection '{vector_service.collection}'")

    # Process local images directly
    print(f"\n4. Processing images and generating embeddings...")
    print(f"   (Processing up to {limit or len(local_images)} images)")

    processed = 0
    failed = 0
    batch_ids = []
    batch_vectors = []
    batch_payloads = []

    images_to_process = local_images[:limit] if limit else local_images

    for i, img_path in enumerate(images_to_process):
        # Extract metadata from filename
        filename = img_path.stem
        parts = filename.split("_")

        # Try to parse brand from filename
        brand = parts[0].title() if parts else "Unknown"
        model = " ".join(parts[1:]).title() if len(parts) > 1 else filename

        # Create payload matching Shoe schema
        payload = {
            "id": str(i),
            "brand": brand,
            "model": model,
            "colorway": "",  # Required field, empty if unknown
            "sku": filename,
            "year": None,
            "aliases": [],
            "images": [str(img_path)],
            "sources": [{"name": "local", "url": str(img_path)}],  # List of SourceRef
            "lastPriceSnapshotAt": None,
        }

        # Generate embedding
        embedding = await embed_image(img_path)
        if embedding is None:
            failed += 1
            continue

        # Add to batch
        point_id = generate_point_id(i, str(img_path))
        batch_ids.append(point_id)
        batch_vectors.append(embedding)
        batch_payloads.append(payload)
        processed += 1

        # Upsert batch
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

        # Progress
        if (i + 1) % 100 == 0:
            print(f"   Progress: {i + 1}/{len(images_to_process)} ({processed} embedded, {failed} failed)")

    # Final batch
    if batch_ids:
        print(f"   Upserting final batch of {len(batch_ids)} vectors...")
        await vector_service.upsert(
            ids=batch_ids,
            vectors=np.array(batch_vectors),
            payloads=batch_payloads
        )

    print(f"\n5. Ingestion complete!")
    print(f"   Successfully processed: {processed}")
    print(f"   Failed: {failed}")
    print("=" * 60)

    conn.close()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest sneaker data into Qdrant")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of images to process")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for upserts")
    args = parser.parse_args()

    await ingest_sneakers(limit=args.limit, batch_size=args.batch_size)


if __name__ == "__main__":
    asyncio.run(main())
