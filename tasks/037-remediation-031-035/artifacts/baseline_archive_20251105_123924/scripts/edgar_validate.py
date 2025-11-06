#!/usr/bin/env python3
"""Validate SEC EDGAR integration with a single Apple 10-K fetch."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from agents.crawler.data_providers.sec_edgar_provider import fetch_10k
from agents.crawler.extractors.pdf_extractor import extract_text


def main() -> int:
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent:
        return _error("SEC_USER_AGENT is required.")
    if "@" not in user_agent:
        return _error("SEC_USER_AGENT must include a contact email address.")

    allow_network = os.getenv("ALLOW_NETWORK", "").lower() == "true"
    if not allow_network:
        return _error("ALLOW_NETWORK must be true to reach the SEC API.")

    try:
        pdf_path = fetch_10k("Apple Inc.", 2024, allow_network=True)
    except Exception as exc:  # pragma: no cover - exercised in integration path
        return _error("fetch_10k failed", exc)

    try:
        chunks = extract_text(pdf_path)
    except Exception as exc:  # pragma: no cover - exercised in integration path
        return _error("PDF extraction failed", exc)

    page_count = len(chunks)

    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as exc:  # pragma: no cover
        return _error("pyarrow is required to write the bronze parquet.", exc)

    rows = [
        {
            "doc_id": str(chunk["doc_id"]),
            "page": int(chunk["page"]),
            "text": str(chunk["text"]),
            "company": "Apple Inc.",
            "year": 2024,
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
    bronze_path = bronze_root / "apple-2024-10k.parquet"
    pq.write_table(table, bronze_path)

    sha256 = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    output = {
        "status": "ok",
        "pdf_path": str(pdf_path),
        "pages": page_count,
        "bronze_path": str(bronze_path),
        "sha256": sha256,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    print(json.dumps(output))
    return 0


def _error(message: str, exc: Exception | None = None) -> int:
    payload = {"status": "error", "message": message}
    if exc is not None:
        payload["detail"] = str(exc)
    print(json.dumps(payload))
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
