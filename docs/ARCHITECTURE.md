## SoleID Architecture

Components:

- Backend (FastAPI): embedding, vector search, pricing aggregation
- Embedding model: OpenCLIP ViT-B/16 (512-D). For tests, set `MOCK_EMBEDDING=true`.
- Qdrant: vector DB, collection `shoes_v1` (512-D, cosine)
- Google Drive: source-of-truth assets and meta.json per SKU
- Android app: capture, quality checks, upload, results, prices

Data Flow:

1. Android captures photo → POST /match (multipart)
2. Backend preprocesses (resize 336, center-crop, normalize) → OpenCLIP ViT-B/16 → 512-D vector
3. Query Qdrant top-k=5 (cosine). Return candidates with payload (Shoe fields)
4. User selects SKU → GET /prices?sku=... → aggregate eBay recent sold → PriceSnapshot

Vector Ingestion:

- `scripts/bootstrap_catalog.py` seeds 50 demo shoes with mock images
- Dedup up to 6 canonical images using phash
- Upsert points id=`{shoe.id}:{fileId}` with payload from `Shoe`

ASCII Diagram:

```
Android  --image-->  FastAPI  --embed-->  Qdrant
   |                     |               ^
   |                     v               |
   +-- GET /prices <-----+--- eBay ------+
```
