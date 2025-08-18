#!/usr/bin/env python3
"""
Re-embed and upsert existing catalog. For demo, call bootstrap.
"""
import subprocess


def main():
    subprocess.check_call(["python", "scripts/bootstrap_catalog.py"])  # reuse demo generator


if __name__ == "__main__":
    main()
