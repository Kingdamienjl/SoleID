## API

### POST /match

Multipart fields:
- image: file

Response:
```json
{
  "candidates": [
    {
      "score": 0.83,
      "shoe": {
        "id": "...",
        "brand": "Nike",
        "model": "Air Jordan 1 Retro High",
        "colorway": "...",
        "sku": "555088-134",
        "images": ["drive://..."]
      }
    }
  ]
}
```

### GET /prices?sku=555088-134

Response:
```json
{
  "sku": "555088-134",
  "asOf": "2024-01-01T00:00:00Z",
  "retail": 170.0,
  "lowestAsk": 390.0,
  "lastSale": 365.0,
  "sourceBreakdown": [
    {"source": "ebay", "median": 360.0, "count": 10}
  ]
}
```
