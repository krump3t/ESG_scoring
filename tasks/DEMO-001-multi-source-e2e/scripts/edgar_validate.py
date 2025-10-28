#!/usr/bin/env python3
"""Task-scoped SEC EDGAR validation helper."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pyarrow as pa  # type: ignore
import pyarrow.parquet as pq  # type: ignore

from agents.crawler.data_providers.sec_edgar_provider import fetch_10k
from agents.crawler.extractors.pdf_extractor import extract_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SEC EDGAR ingestion for DEMO-001.")
    parser.add_argument("--company", default="Apple Inc.", help="Company to fetch (default: Apple Inc.)")
    parser.add_argument("--year", type=int, default=2024, help="Filing year (default: 2024)")
    return parser.parse_args()


def main() -> int:
    if os.getenv("ALLOW_NETWORK", "").lower() != "true":
        return _error("ALLOW_NETWORK must be set to 'true'.")
    if os.getenv("LIVE_EMBEDDINGS", "").lower() != "true":
        return _error("LIVE_EMBEDDINGS must be 'true' for live validation.")
    for key in ("SEC_USER_AGENT", "WX_API_KEY", "WX_PROJECT", "WX_MODEL_ID"):
        if not os.getenv(key):
            return _error(f"{key} is required.")

    args = parse_args()
    try:
        pdf_path = fetch_10k(args.company, args.year, allow_network=True)
    except Exception as exc:  # pragma: no cover - exercised in integration flow
        return _error("Failed to fetch SEC filing.", exc)

    try:
        chunks = extract_text(pdf_path)
    except Exception as exc:  # pragma: no cover
        return _error("PDF extraction failed.", exc)

    rows = [
        {
            "doc_id": chunk["doc_id"],
            "page": chunk["page"],
            "text": chunk["text"],
            "company": args.company,
            "year": args.year,
        }
        for chunk in chunks
    ]

    schema = pa.schema(
        [
            ("doc_id", pa.string()),
            ("page", pa.int32()),
            ("text", pa.string()),
            ("company", pa.string()),
            ("year", pa.int32()),
        ]
    )
    table = pa.Table.from_pylist(rows, schema=schema)

    bronze_root = Path(os.getenv("DATA_ROOT", "artifacts")) / "tmp"
    bronze_root.mkdir(parents=True, exist_ok=True)
    bronze_path = bronze_root / f"{args.company.lower().replace(' ', '-')}-{args.year}-10k.parquet"
    pq.write_table(table, bronze_path)

    sha256 = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    payload = {
        "status": "ok",
        "company": args.company,
        "year": args.year,
        "pages": len(chunks),
        "pdf_path": str(pdf_path),
        "bronze_path": str(bronze_path),
        "sha256": sha256,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
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
    sys.exit(main())
