"""Monthly budget guard for vision identify calls.

Counters live in the shared cache (Redis when configured, in-memory
otherwise) under a per-month key. Two independent limits, both
env-configurable:

- VISION_MONTHLY_CALL_CAP  (default 5000)  — hard cap on identify calls
- VISION_MONTHLY_BUDGET_USD (default 5.0)  — hard cap on estimated spend

The default provider (Gemini Flash free tier) costs $0 within quota, so
in practice the call cap is the binding limit; the USD cap protects the
deployment if a paid fallback model is ever configured.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from app.services.cache import get_cache

logger = logging.getLogger("soleid.vision.budget")


class BudgetExceeded(Exception):
    """Raised when a monthly vision limit has been reached."""


def _month_key() -> str:
    now = datetime.now(timezone.utc)
    return f"vision:usage:{now.year:04d}-{now.month:02d}"


def _limits() -> tuple[int, float]:
    calls = int(os.getenv("VISION_MONTHLY_CALL_CAP", "5000"))
    usd = float(os.getenv("VISION_MONTHLY_BUDGET_USD", "5.0"))
    return calls, usd


async def _read_usage() -> dict:
    cache = get_cache()
    raw = await cache.get(_month_key())
    if raw is None:
        return {"calls": 0, "estUsd": 0.0}
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"calls": 0, "estUsd": 0.0}
    return raw  # in-memory cache may hand back the stored object


async def check_budget(est_cost_usd: float) -> None:
    """Raise BudgetExceeded if one more call would cross a monthly limit."""
    usage = await _read_usage()
    call_cap, usd_cap = _limits()
    if usage.get("calls", 0) + 1 > call_cap:
        raise BudgetExceeded(
            f"monthly vision call cap reached ({call_cap})"
        )
    if usage.get("estUsd", 0.0) + est_cost_usd > usd_cap:
        raise BudgetExceeded(
            f"monthly vision budget reached (${usd_cap:.2f})"
        )


async def record_call(est_cost_usd: float) -> None:
    usage = await _read_usage()
    usage["calls"] = usage.get("calls", 0) + 1
    usage["estUsd"] = usage.get("estUsd", 0.0) + est_cost_usd
    cache = get_cache()
    # 40 days: outlives the month the key belongs to.
    await cache.set(_month_key(), json.dumps(usage), ttl_seconds=40 * 24 * 3600)
    logger.info(
        "vision usage this month: calls=%s estUsd=%.4f",
        usage["calls"],
        usage["estUsd"],
    )
