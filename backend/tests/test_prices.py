from fastapi.testclient import TestClient
from app.main import app


def test_prices_endpoint_mock():
    client = TestClient(app)
    resp = client.get("/prices", params={"sku": "555088-134"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sku"] == "555088-134"
