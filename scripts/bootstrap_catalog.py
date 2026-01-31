#!/usr/bin/env python3
"""
Seed the sneaker catalog with popular shoes and upsert vectors.

This script populates the Qdrant database with real sneaker data
including popular Nike, Jordan, Adidas, and other brand models.
"""
import asyncio
import uuid
from typing import List, Callable
from PIL import Image

from app.schemas.shoe import Shoe, SourceRef
from app.services.ingest import upsert_shoes


# Real popular sneakers data
SNEAKER_CATALOG = [
    # Nike Air Jordan 1s
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro High OG",
        "colorway": "Chicago",
        "sku": "555088-101",
        "year": 2015,
        "aliases": ["AJ1", "Jordan 1", "Chicago 1s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro High OG",
        "colorway": "Bred",
        "sku": "555088-001",
        "year": 2016,
        "aliases": ["AJ1", "Jordan 1", "Banned", "Bred 1s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro High OG",
        "colorway": "Royal Blue",
        "sku": "555088-007",
        "year": 2017,
        "aliases": ["AJ1", "Jordan 1", "Royal 1s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro High OG",
        "colorway": "Shadow",
        "sku": "555088-013",
        "year": 2018,
        "aliases": ["AJ1", "Jordan 1", "Shadow 1s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro High OG",
        "colorway": "University Blue",
        "sku": "555088-134",
        "year": 2021,
        "aliases": ["AJ1", "Jordan 1", "UNC 1s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro High OG",
        "colorway": "Dark Mocha",
        "sku": "555088-105",
        "year": 2020,
        "aliases": ["AJ1", "Jordan 1", "Mocha 1s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro High OG",
        "colorway": "Travis Scott",
        "sku": "CD4487-100",
        "year": 2019,
        "aliases": ["AJ1", "Jordan 1", "Travis Scott", "Cactus Jack"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 1 Retro Low OG",
        "colorway": "Travis Scott",
        "sku": "CQ4277-001",
        "year": 2019,
        "aliases": ["AJ1 Low", "Jordan 1 Low", "Travis Scott Low"],
    },
    # Air Jordan 4s
    {
        "brand": "Jordan",
        "model": "Air Jordan 4 Retro",
        "colorway": "White Cement",
        "sku": "840606-192",
        "year": 2016,
        "aliases": ["AJ4", "Jordan 4", "White Cement 4s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 4 Retro",
        "colorway": "Bred",
        "sku": "308497-060",
        "year": 2019,
        "aliases": ["AJ4", "Jordan 4", "Bred 4s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 4 Retro",
        "colorway": "Fire Red",
        "sku": "DC7770-160",
        "year": 2020,
        "aliases": ["AJ4", "Jordan 4", "Fire Red 4s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 4 Retro",
        "colorway": "University Blue",
        "sku": "CT8527-400",
        "year": 2021,
        "aliases": ["AJ4", "Jordan 4", "UNC 4s"],
    },
    # Air Jordan 11s
    {
        "brand": "Jordan",
        "model": "Air Jordan 11 Retro",
        "colorway": "Concord",
        "sku": "378037-100",
        "year": 2018,
        "aliases": ["AJ11", "Jordan 11", "Concord 11s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 11 Retro",
        "colorway": "Bred",
        "sku": "378037-061",
        "year": 2019,
        "aliases": ["AJ11", "Jordan 11", "Bred 11s", "Playoffs"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 11 Retro",
        "colorway": "Space Jam",
        "sku": "378037-003",
        "year": 2016,
        "aliases": ["AJ11", "Jordan 11", "Space Jam 11s"],
    },
    # Nike Dunks
    {
        "brand": "Nike",
        "model": "Dunk Low",
        "colorway": "Panda",
        "sku": "DD1391-100",
        "year": 2021,
        "aliases": ["Dunk", "Panda Dunks", "Black White Dunk"],
    },
    {
        "brand": "Nike",
        "model": "Dunk Low",
        "colorway": "University Red",
        "sku": "DD1391-600",
        "year": 2021,
        "aliases": ["Dunk", "Red Dunks"],
    },
    {
        "brand": "Nike",
        "model": "Dunk Low",
        "colorway": "Coast",
        "sku": "DD1503-100",
        "year": 2021,
        "aliases": ["Dunk", "Coast Dunks", "UCLA Dunks"],
    },
    {
        "brand": "Nike",
        "model": "Dunk Low",
        "colorway": "Kentucky",
        "sku": "CU1726-100",
        "year": 2020,
        "aliases": ["Dunk", "Kentucky Dunks"],
    },
    {
        "brand": "Nike",
        "model": "SB Dunk Low",
        "colorway": "Travis Scott",
        "sku": "CT5053-001",
        "year": 2020,
        "aliases": ["SB Dunk", "Travis Scott Dunk", "Cactus Jack Dunk"],
    },
    {
        "brand": "Nike",
        "model": "SB Dunk Low",
        "colorway": "Strangelove",
        "sku": "CT2552-800",
        "year": 2020,
        "aliases": ["SB Dunk", "Strangelove Dunk", "Valentine Dunk"],
    },
    # Nike Air Force 1
    {
        "brand": "Nike",
        "model": "Air Force 1 Low",
        "colorway": "White",
        "sku": "315122-111",
        "year": 2020,
        "aliases": ["AF1", "Air Force 1", "Triple White AF1"],
    },
    {
        "brand": "Nike",
        "model": "Air Force 1 Low",
        "colorway": "Black",
        "sku": "315122-001",
        "year": 2020,
        "aliases": ["AF1", "Air Force 1", "Triple Black AF1"],
    },
    # Nike Air Max
    {
        "brand": "Nike",
        "model": "Air Max 1",
        "colorway": "Anniversary Red",
        "sku": "908375-103",
        "year": 2017,
        "aliases": ["AM1", "Air Max 1", "OG Red"],
    },
    {
        "brand": "Nike",
        "model": "Air Max 90",
        "colorway": "Infrared",
        "sku": "CT1685-100",
        "year": 2020,
        "aliases": ["AM90", "Air Max 90", "Infrared 90"],
    },
    {
        "brand": "Nike",
        "model": "Air Max 97",
        "colorway": "Silver Bullet",
        "sku": "884421-001",
        "year": 2017,
        "aliases": ["AM97", "Air Max 97", "Silver Bullet"],
    },
    # Adidas Yeezy
    {
        "brand": "Adidas",
        "model": "Yeezy Boost 350 V2",
        "colorway": "Zebra",
        "sku": "CP9654",
        "year": 2017,
        "aliases": ["Yeezy", "350 V2", "Zebra Yeezy"],
    },
    {
        "brand": "Adidas",
        "model": "Yeezy Boost 350 V2",
        "colorway": "Bred",
        "sku": "CP9652",
        "year": 2017,
        "aliases": ["Yeezy", "350 V2", "Bred Yeezy"],
    },
    {
        "brand": "Adidas",
        "model": "Yeezy Boost 350 V2",
        "colorway": "Beluga",
        "sku": "BB1826",
        "year": 2016,
        "aliases": ["Yeezy", "350 V2", "Beluga Yeezy"],
    },
    {
        "brand": "Adidas",
        "model": "Yeezy Boost 350 V2",
        "colorway": "Cream White",
        "sku": "CP9366",
        "year": 2017,
        "aliases": ["Yeezy", "350 V2", "Cream Yeezy", "Triple White Yeezy"],
    },
    {
        "brand": "Adidas",
        "model": "Yeezy Boost 700",
        "colorway": "Wave Runner",
        "sku": "B75571",
        "year": 2018,
        "aliases": ["Yeezy 700", "Wave Runner"],
    },
    {
        "brand": "Adidas",
        "model": "Yeezy Slide",
        "colorway": "Onyx",
        "sku": "HQ6448",
        "year": 2022,
        "aliases": ["Yeezy Slide", "Onyx Slide"],
    },
    # Adidas Originals
    {
        "brand": "Adidas",
        "model": "Stan Smith",
        "colorway": "White Green",
        "sku": "M20324",
        "year": 2020,
        "aliases": ["Stan Smith", "Classic Stan Smith"],
    },
    {
        "brand": "Adidas",
        "model": "Superstar",
        "colorway": "White Black",
        "sku": "EG4958",
        "year": 2020,
        "aliases": ["Superstar", "Shell Toe"],
    },
    {
        "brand": "Adidas",
        "model": "Samba OG",
        "colorway": "White Black",
        "sku": "B75806",
        "year": 2023,
        "aliases": ["Samba", "Samba OG"],
    },
    # New Balance
    {
        "brand": "New Balance",
        "model": "550",
        "colorway": "White Green",
        "sku": "BB550WT1",
        "year": 2021,
        "aliases": ["NB 550", "550"],
    },
    {
        "brand": "New Balance",
        "model": "550",
        "colorway": "White Navy",
        "sku": "BB550WA1",
        "year": 2021,
        "aliases": ["NB 550", "550"],
    },
    {
        "brand": "New Balance",
        "model": "990v5",
        "colorway": "Grey",
        "sku": "M990GL5",
        "year": 2019,
        "aliases": ["NB 990", "990v5", "Dad Shoe"],
    },
    {
        "brand": "New Balance",
        "model": "2002R",
        "colorway": "Protection Pack Rain Cloud",
        "sku": "M2002RDA",
        "year": 2022,
        "aliases": ["NB 2002R", "2002R"],
    },
    # Asics
    {
        "brand": "Asics",
        "model": "Gel-Kayano 14",
        "colorway": "White Midnight",
        "sku": "1201A019-102",
        "year": 2023,
        "aliases": ["Kayano 14", "GK14"],
    },
    {
        "brand": "Asics",
        "model": "Gel-NYC",
        "colorway": "White Navy",
        "sku": "1203A280-103",
        "year": 2023,
        "aliases": ["Gel NYC"],
    },
    # Converse
    {
        "brand": "Converse",
        "model": "Chuck Taylor All Star",
        "colorway": "White High Top",
        "sku": "M7650",
        "year": 2020,
        "aliases": ["Chucks", "Chuck Taylor", "All Star"],
    },
    {
        "brand": "Converse",
        "model": "Chuck 70",
        "colorway": "Black High Top",
        "sku": "162050C",
        "year": 2020,
        "aliases": ["Chuck 70", "Chucks"],
    },
    # Puma
    {
        "brand": "Puma",
        "model": "Suede Classic",
        "colorway": "Black White",
        "sku": "352634-03",
        "year": 2020,
        "aliases": ["Puma Suede", "Suede Classic"],
    },
    # Reebok
    {
        "brand": "Reebok",
        "model": "Club C 85",
        "colorway": "White Green",
        "sku": "AR0456",
        "year": 2020,
        "aliases": ["Club C", "Club C 85"],
    },
    {
        "brand": "Reebok",
        "model": "Classic Leather",
        "colorway": "White",
        "sku": "49797",
        "year": 2020,
        "aliases": ["CL Leather", "Classic Leather"],
    },
    # More Jordan models
    {
        "brand": "Jordan",
        "model": "Air Jordan 3 Retro",
        "colorway": "White Cement",
        "sku": "DN3707-100",
        "year": 2023,
        "aliases": ["AJ3", "Jordan 3", "White Cement 3s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 5 Retro",
        "colorway": "Fire Red",
        "sku": "DA1911-102",
        "year": 2020,
        "aliases": ["AJ5", "Jordan 5", "Fire Red 5s"],
    },
    {
        "brand": "Jordan",
        "model": "Air Jordan 6 Retro",
        "colorway": "Carmine",
        "sku": "CT8529-106",
        "year": 2021,
        "aliases": ["AJ6", "Jordan 6", "Carmine 6s"],
    },
]


def _make_shoes() -> List[Shoe]:
    """Create Shoe objects from the catalog."""
    shoes = []
    for data in SNEAKER_CATALOG:
        shoes.append(
            Shoe(
                id=str(uuid.uuid4()),
                brand=data["brand"],
                model=data["model"],
                colorway=data["colorway"],
                sku=data["sku"],
                year=data.get("year"),
                aliases=data.get("aliases", []),
                images=[],  # Will be populated when images are available
                sources=[SourceRef(name="ebay", url="https://www.ebay.com")],
                lastPriceSnapshotAt=None,
            )
        )
    return shoes


def _fake_image_loader(file_id: str) -> Image.Image:
    """Generate a placeholder image based on file_id hash."""
    h = abs(hash(file_id)) % 255
    img = Image.new("RGB", (400, 400), color=(h, 255 - h, (h * 2) % 255))
    return img


async def _main():
    shoes = _make_shoes()
    print(f"Seeding {len(shoes)} sneakers to the catalog...")

    await upsert_shoes(shoes, image_loader=_fake_image_loader)

    print(f"Successfully seeded {len(shoes)} sneakers with vectors")
    print("\nBrands included:")
    brands = set(s.brand for s in shoes)
    for brand in sorted(brands):
        count = sum(1 for s in shoes if s.brand == brand)
        print(f"  - {brand}: {count} shoes")


if __name__ == "__main__":
    asyncio.run(_main())
