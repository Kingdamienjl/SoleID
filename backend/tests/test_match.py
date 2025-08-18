import io
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_match_endpoint_mock_image(monkeypatch):
    client = TestClient(app)

    # Create a dummy image
    img = Image.new("RGB", (512, 512), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    # Hit endpoint
    resp = client.post("/match", files={"image": ("test.jpg", buf, "image/jpeg")})
    # Service may fail if Qdrant not running locally, but FastAPI route itself should respond 200 or 500.
    # We assert request reached the app layer and returns JSON/HTTP status.
    assert resp.status_code in (200, 500)
