from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user
from app.services.auth import FirebaseUser


def _fake_user() -> FirebaseUser:
    return FirebaseUser(
        uid="test-user",
        email="test@example.com",
        email_verified=True,
        name="Test User",
        picture=None,
        auth_time=0,
    )


def test_prices_requires_auth():
    client = TestClient(app)
    resp = client.get("/prices", params={"sku": "555088-134"})
    assert resp.status_code == 401


def test_prices_endpoint_mock():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/prices", params={"sku": "555088-134"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sku"] == "555088-134"
    finally:
        app.dependency_overrides.clear()
