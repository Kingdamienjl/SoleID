import json
from pathlib import Path
from app.main import app

def main() -> None:
    schema = app.openapi()
    out = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2))
    print(f"Wrote OpenAPI schema to {out}")

if __name__ == "__main__":
    main()

