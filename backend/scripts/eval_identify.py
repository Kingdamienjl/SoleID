#!/usr/bin/env python3
"""Phase 0 eval harness for the vision-first pivot.

Runs the configured vision provider chain (GEMINI_API_KEY and/or
OPENROUTER_API_KEY from the environment) against a labeled dataset and
scores it:

- top-1 accuracy: primary styleId == expected styleId
- top-3 accuracy: expected styleId appears in primary + alternates
- wrong-confident rate: primary wrong while confidence >= threshold
  (the metric the pivot gate cares about most)

Dataset: backend/eval/dataset.csv with columns
  image,style_id,brand,name,notes
where `image` is a path relative to backend/eval/.

Usage:
  GEMINI_API_KEY=... python scripts/eval_identify.py [--dataset PATH]
      [--threshold 0.75] [--delay 2.0] [--out results.csv]

The incumbent CLIP/Qdrant path is scored by pointing the same photos at
the running app's /match endpoint and comparing styleIds the same way —
see backend/eval/README.md.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.vision import get_vision_providers  # noqa: E402
from app.services.vision.base import VisionProviderError  # noqa: E402

MIME_BY_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def normalize_sku(s: str | None) -> str:
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(Path(__file__).resolve().parents[1] / "eval" / "dataset.csv"))
    ap.add_argument("--threshold", type=float, default=0.75)
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between calls (free-tier rate limits)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    providers = get_vision_providers()
    if not providers:
        print("ERROR: no vision provider configured — set GEMINI_API_KEY or OPENROUTER_API_KEY")
        return 2
    provider = providers[0]
    print(f"provider: {provider.name} | dataset: {args.dataset} | threshold: {args.threshold}")

    dataset_path = Path(args.dataset)
    rows = list(csv.DictReader(dataset_path.open()))
    if not rows:
        print("ERROR: dataset is empty — see backend/eval/README.md")
        return 2

    out_path = Path(args.out) if args.out else dataset_path.parent / "eval_results.csv"
    results = []
    top1 = top3 = wrong_conf = errors = 0

    for i, row in enumerate(rows, 1):
        img_path = dataset_path.parent / row["image"]
        expected = normalize_sku(row["style_id"])
        entry = {"image": row["image"], "expected": row["style_id"], "predicted": "",
                 "confidence": "", "top1": 0, "top3": 0, "wrong_confident": 0, "model": "", "error": ""}
        try:
            data = img_path.read_bytes()
            mime = MIME_BY_EXT.get(img_path.suffix.lower(), "image/jpeg")
            result = await provider.identify(data, mime)
            entry["model"] = result.model
            if not result.is_shoe or result.primary is None:
                entry["error"] = "provider says not a shoe"
                errors += 1
            else:
                predicted = normalize_sku(result.primary.styleId)
                entry["predicted"] = result.primary.styleId or ""
                entry["confidence"] = f"{result.primary.confidence:.2f}"
                candidates = [result.primary, *result.alternates]
                hit1 = bool(expected) and predicted == expected
                hit3 = any(normalize_sku(c.styleId) == expected for c in candidates if c.styleId)
                entry["top1"] = int(hit1)
                entry["top3"] = int(hit3)
                top1 += hit1
                top3 += hit3
                if not hit1 and result.primary.confidence >= args.threshold:
                    entry["wrong_confident"] = 1
                    wrong_conf += 1
        except (VisionProviderError, OSError) as exc:
            entry["error"] = str(exc)[:200]
            errors += 1
        results.append(entry)
        print(f"[{i}/{len(rows)}] {row['image']}: top1={entry['top1']} top3={entry['top3']} "
              f"wrong_conf={entry['wrong_confident']} {entry['error']}")
        if i < len(rows) and args.delay:
            time.sleep(args.delay)

    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    n = len(rows)
    print("\n=== EVAL SUMMARY ===")
    print(f"rows: {n}  errors: {errors}")
    print(f"top-1 accuracy:      {top1}/{n} = {top1 / n:.1%}")
    print(f"top-3 accuracy:      {top3}/{n} = {top3 / n:.1%}")
    print(f"wrong-confident:     {wrong_conf}/{n} = {wrong_conf / n:.1%}  (gate: near zero)")
    print(f"results written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
