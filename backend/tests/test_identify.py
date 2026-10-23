import io

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user
from app.services.auth import FirebaseUser
from app.schemas.price import PriceSnapshot, SourceBreakdown
from app.services.vision.base import ShoeCandidate, VisionProvider, VisionResult
import app.services.identify as identify_mod


def _fake_user() -> FirebaseUser:
    return FirebaseUser(
        uid="test-user",
        email="test@example.com",
        email_verified=True,
        name="Test User",
        picture=None,
        auth_time=0,
    )


def _img_bytes(color=(10, 20, 30)) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class FakeProvider(VisionProvider):
    name = "fake"
    est_cost_usd = 0.0

    def __init__(self, result: VisionResult):
        self.result = result
        self.calls = 0

    async def identify(self, image_bytes: bytes, mime_type: str) -> VisionResult:
        self.calls += 1
        return self.result


class FakeAggregator:
    def __init__(self, snapshot: PriceSnapshot):
        self.snapshot = snapshot

    async def get_aggregated_prices(self, sku, include_sources=None):
        return self.snapshot


def _live_snapshot(sku="DZ5485-612") -> PriceSnapshot:
    return PriceSnapshot(
        sku=sku,
        asOf="2026-10-23T00:00:00Z",
        lowestAsk=210.0,
        sourceBreakdown=[
            SourceBreakdown(source="stockx", lowest=210.0, buyUrl="https://stockx.com/x")
        ],
        dataSource="live",
    )


def _fallback_snapshot(sku="DZ5485-612") -> PriceSnapshot:
    return PriceSnapshot(
        sku=sku,
        asOf="2026-10-23T00:00:00Z",
        lowestAsk=190.0,
        sourceBreakdown=[
            SourceBreakdown(source="stockx", lowest=190.0, isMock=True)
        ],
        dataSource="fallback",
    )


def _jordan_result(confidence=0.93) -> VisionResult:
    return VisionResult(
        is_shoe=True,
        primary=ShoeCandidate(
            brand="Nike",
            name="Air Jordan 1 Retro High OG",
            colorway="Lost and Found",
            styleId="DZ5485-612",
            confidence=confidence,
        ),
        alternates=[],
        model="fake-v1",
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _client() -> TestClient:
    app.dependency_overrides[get_current_user] = _fake_user
    return TestClient(app, raise_server_exceptions=False)


def _post(client: TestClient, color=(10, 20, 30)):
    return client.post(
        "/identify",
        files={"image": ("shoe.jpg", io.BytesIO(_img_bytes(color)), "image/jpeg")},
    )


def test_identify_requires_auth():
    client = TestClient(app, raise_server_exceptions=False)
    resp = _post(client)
    assert resp.status_code == 401


def test_identify_disabled_by_default(monkeypatch):
    monkeypatch.delenv("IDENTIFY_ENABLED", raising=False)
    resp = _post(_client())
    assert resp.status_code == 503


def test_identify_happy_path(monkeypatch):
    monkeypatch.setenv("IDENTIFY_ENABLED", "1")
    provider = FakeProvider(_jordan_result())
    monkeypatch.setattr(identify_mod, "get_vision_providers", lambda: [provider])
    monkeypatch.setattr(
        identify_mod, "get_price_aggregator", lambda: FakeAggregator(_live_snapshot())
    )
    resp = _post(_client(), color=(200, 10, 10))
    assert resp.status_code == 200
    data = resp.json()
    assert data["shoe"]["brand"] == "Nike"
    assert data["shoe"]["styleId"] == "DZ5485-612"
    assert data["skuVerified"] is True
    assert data["source"].startswith("vision:")
    assert data["prices"]["dataSource"] == "live"


def test_identify_not_a_shoe(monkeypatch):
    monkeypatch.setenv("IDENTIFY_ENABLED", "1")
    provider = FakeProvider(VisionResult(is_shoe=False, model="fake-v1"))
    monkeypatch.setattr(identify_mod, "get_vision_providers", lambda: [provider])
    resp = _post(_client(), color=(10, 200, 10))
    assert resp.status_code == 400


def test_identify_low_confidence_returns_candidates(monkeypatch):
    monkeypatch.setenv("IDENTIFY_ENABLED", "1")
    provider = FakeProvider(_jordan_result(confidence=0.4))
    monkeypatch.setattr(identify_mod, "get_vision_providers", lambda: [provider])
    monkeypatch.setattr(
        identify_mod, "get_price_aggregator", lambda: FakeAggregator(_live_snapshot())
    )
    resp = _post(_client(), color=(10, 10, 200))
    assert resp.status_code == 200
    data = resp.json()
    assert data["shoe"] is None
    assert len(data["candidates"]) >= 1
    assert data["candidates"][0]["brand"] == "Nike"


def test_identify_unverified_sku_returns_candidates(monkeypatch):
    monkeypatch.setenv("IDENTIFY_ENABLED", "1")
    provider = FakeProvider(_jordan_result(confidence=0.95))
    monkeypatch.setattr(identify_mod, "get_vision_providers", lambda: [provider])
    monkeypatch.setattr(
        identify_mod,
        "get_price_aggregator",
        lambda: FakeAggregator(_fallback_snapshot()),
    )
    resp = _post(_client(), color=(200, 200, 10))
    assert resp.status_code == 200
    data = resp.json()
    assert data["shoe"] is None
    assert data["skuVerified"] is False


def test_identify_budget_exceeded(monkeypatch):
    monkeypatch.setenv("IDENTIFY_ENABLED", "1")
    provider = FakeProvider(_jordan_result())
    monkeypatch.setattr(identify_mod, "get_vision_providers", lambda: [provider])

    async def _boom(_cost):
        from app.services.vision.budget import BudgetExceeded

        raise BudgetExceeded("monthly vision call cap reached (5000)")

    monkeypatch.setattr(identify_mod, "check_budget", _boom)
    resp = _post(_client(), color=(200, 10, 200))
    assert resp.status_code == 429


def test_identify_second_call_hits_l1_cache(monkeypatch):
    import asyncio

    provider = FakeProvider(_jordan_result())
    monkeypatch.setattr(identify_mod, "get_vision_providers", lambda: [provider])
    monkeypatch.setattr(
        identify_mod, "get_price_aggregator", lambda: FakeAggregator(_live_snapshot())
    )
    img = _img_bytes(color=(99, 88, 77))

    async def _run():
        first = await identify_mod.identify_shoe(img, "image/jpeg")
        second = await identify_mod.identify_shoe(img, "image/jpeg")
        return first, second

    first, second = asyncio.run(_run())
    assert provider.calls == 1
    assert first.source.startswith("vision:")
    assert second.source == "cache"
    assert second.shoe.brand == "Nike"
