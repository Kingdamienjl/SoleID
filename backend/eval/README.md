# Vision identification eval — Phase 0 of the pivot

The pivot ships only if the vision path beats the incumbent CLIP/Qdrant
path on the same photos. This folder holds the dataset that decides it.

## Build the dataset

Target **75–100 photos**. Mix:

- Your own shoe photos (phone shots, imperfect light/angles — the real use case)
- Clean product shots
- **Hard cases on purpose:**
  - Same silhouette, different colorway (Jordan 1 Bred vs Chicago vs Royal)
  - Retro vs OG of the same shoe
  - Collabs vs GR versions of the same model
  - Similar models from different brands

Layout:

```
eval/
  dataset.csv
  images/
    DZ5485-612_1.jpg
    DD1391-100_1.jpg
    ...
```

`dataset.csv` columns: `image,style_id,brand,name,notes`

- `image` — path relative to this folder, e.g. `images/DZ5485-612_1.jpg`
- `style_id` — ground-truth manufacturer style code, verified against a
  StockX/GOAT listing (not from memory)
- `notes` — what makes the case hard, if anything

Photos of your own shoes only — do not commit other people's photos you
don't have rights to. `eval/images/` is gitignored; the CSV (labels only)
is committed.

## Run it

From `backend/`:

```bash
GEMINI_API_KEY=<key> python scripts/eval_identify.py
```

(The key lives in `K:\Backup\Api Keys\GEMINI_API_KEY.txt` — load it into
the environment wherever you run this; never commit it.)

Outputs per-photo results to `eval/eval_results.csv` and prints:

- **top-1 accuracy** — primary guess exactly right
- **top-3 accuracy** — right answer inside primary + alternates
- **wrong-confident rate** — wrong while claiming ≥0.75 confidence.
  This is the gate metric: the pivot ships only if this is near zero
  AND top-1 ≥ the incumbent pipeline's top-1 on the same set.

## Scoring the incumbent

Run the same photos through the deployed app's `/match`, take the top
candidate's SKU per photo, and compute the same three numbers. The
comparison — not either number alone — decides Phase 2 of the pivot.
