"""
Keep-alive pinger for SoleID services.
Prevents free-tier services from idling out.

Usage:
    python keep-alive.py                    # Run once
    python keep-alive.py --loop             # Run every 10 minutes
    python keep-alive.py --loop --interval 300  # Run every 5 minutes

Set environment variables or edit the URLs below.
"""

import os
import sys
import time
import argparse
import urllib.request
import urllib.error
import json
from datetime import datetime


# --- Configure your service URLs here ---
SERVICES = {
    "qdrant": {
        "url": os.getenv(
            "QDRANT_URL",
            "https://edb3e772-e52f-4766-8072-e0ba6651bd20.us-east4-0.gcp.cloud.qdrant.io:6333/collections",
        ),
        "headers": {
            "api-key": os.getenv(
                "QDRANT_API_KEY",
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.eqrowlyem81woO8SFksJeYwzNpC080kCus6jv9l5bPM",
            )
        },
    },
    "backend": {
        "url": os.getenv("BACKEND_URL", "https://soleid-backend-512523849627.us-central1.run.app/health"),
        "headers": {},
    },
}


def ping(name: str, url: str, headers: dict) -> bool:
    if not url:
        return True  # Skip unconfigured services
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            print(f"  [{name}] {status} OK - {url[:60]}...")
            return True
    except urllib.error.HTTPError as e:
        print(f"  [{name}] HTTP {e.code} - {url[:60]}...")
        return e.code < 500  # 4xx is "alive", 5xx is not
    except Exception as e:
        print(f"  [{name}] FAILED - {e}")
        return False


def run_once() -> int:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n--- Keep-alive ping at {ts} ---")
    failures = 0
    for name, cfg in SERVICES.items():
        if not cfg["url"]:
            continue
        if not ping(name, cfg["url"], cfg["headers"]):
            failures += 1
    return failures


def main():
    parser = argparse.ArgumentParser(description="SoleID keep-alive pinger")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=600, help="Seconds between pings (default: 600 = 10 min)")
    args = parser.parse_args()

    if args.loop:
        print(f"Keep-alive running every {args.interval}s. Press Ctrl+C to stop.")
        while True:
            run_once()
            time.sleep(args.interval)
    else:
        failures = run_once()
        sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
