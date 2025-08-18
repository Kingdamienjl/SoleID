## Data Model

Shoe (normalized):

```
{
  "id": "<UUID>",
  "brand": "Nike|Adidas|New Balance|…",
  "model": "Air Jordan 1 Retro High",
  "colorway": "University Blue/Black-White",
  "sku": "555088-134",
  "year": 2021,
  "aliases": ["AJ1 UNC", "Jordan 1 UNC"],
  "images": ["drive://fileId1", "drive://fileId2"],
  "sources": [{"name":"ebay","url":"..."},{"name":"flightclub","url":"..."}],
  "lastPriceSnapshotAt": "ISO8601"
}
```

Embedding/Collection:

- collection: `shoes_v1`
- vector dim: 512
- payload keys: id, brand, model, colorway, sku

PriceSnapshot:

```
{
  "sku": "555088-134",
  "asOf": "ISO8601",
  "retail": 170.0,
  "lowestAsk": 390.0,
  "lastSale": 365.0,
  "sourceBreakdown": [{"source":"ebay","median":...,"count":...}]
}
```
