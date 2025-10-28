#!/usr/bin/env python3
"""Validate Headlam SEC ingestion for the live path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from agents.crawler.data_providers.sec_edgar_provider import fetch_10k
from agents.crawler.extractors.pdf_extractor import extract_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SEC 10-K retrieval for Headlam.")
    parser.add_argument("--company", default="Headlam Group Plc")
    parser.add_argument("--year", type=int, default=2025)
    return parser.parse_args()


def main() -> int:
    if os.getenv("ALLOW_NETWORK", "").lower() != "true":
        return _error("ALLOW_NETWORK must be 'true'.")
    if os.getenv("LIVE_EMBEDDINGS", "").lower() != "true":
        return _error("LIVE_EMBEDDINGS must be 'true'.")
    if not os.getenv("SEC_USER_AGENT"):
        return _error("SEC_USER_AGENT is required.")

    args = parse_args()
    pdf_path = fetch_10k(args.company, args.year, allow_network=True)
    chunks = extract_text(pdf_path)
    if not chunks:
        return _error("PDF extraction returned no text.")

    df = pd.DataFrame(chunks)
    bronze_root = Path(os.getenv("DATA_ROOT", "artifacts")) / "tmp"
    bronze_root.mkdir(parents=True, exist_ok=True)
    bronze_path = bronze_root / "headlam-2025-10k.parquet"
    df.to_parquet(bronze_path, index=False)

    sha256 = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    payload = {
        "status": "ok",
        "company": args.company,
        "year": args.year,
        "pages": len(chunks),
        "pdf_path": str(pdf_path),
        "bronze_path": str(bronze_path),
        "sha256": sha256,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    print(json.dumps(payload))
    return 0


def _error(message: str, exc: Exception | None = None) -> int:
    payload = {"status": "error", "message": message}
    if exc is not None:
        payload["detail"] = str(exc)
    print(json.dumps(payload))
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
