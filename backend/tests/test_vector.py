import os


def test_qdrant_env_defaults():
    # Ensure defaults are present for local dev
    assert os.getenv("QDRANT_URL", "http://localhost:6333").startswith("http")
