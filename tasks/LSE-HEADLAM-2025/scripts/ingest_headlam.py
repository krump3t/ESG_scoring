#!/usr/bin/env python3
"""Ingest Headlam 2025 sustainability report into deterministic bronze storage."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

from apps.utils.provenance import sha256_text
from agents.crawler.extractors.pdf_extractor import extract_text

TASK_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("artifacts")
TASK_ARTIFACT_DIR = DATA_ROOT / "tasks" / "LSE-HEADLAM-2025"
TASK_BRONZE_DIR = TASK_ARTIFACT_DIR / "bronze"
BRONZE_TASK_PATH = TASK_BRONZE_DIR / "chunks.parquet"
BRONZE_GLOBAL_PATH = DATA_ROOT / "bronze" / "headlam_group_plc_2025.parquet"
CONTEXT_PATH = TASK_ROOT / "context" / "demo_manifest.json"
COMPANIES_MANIFEST = DATA_ROOT / "demo" / "companies.json"
PDF_PATH = Path("/mnt/data/LSE_HEAD_2025.pdf")


def build_bronze(update_manifest: bool = True) -> Path:
    """Extract PDF chunks and persist bronze parquet files."""
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found at {PDF_PATH}")

    pdf_bytes = PDF_PATH.read_bytes()
    pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()

    chunks = extract_text(PDF_PATH)
    if not chunks:
        raise RuntimeError("No text extracted from Headlam PDF.")

    rows: List[dict] = []
    for chunk in chunks:
        page = int(chunk["page"])
        doc_id = f"headlam-sustainability-2025:{page:04d}"
        text = str(chunk["text"]).strip()
        rows.append(
            {
                "doc_id": doc_id,
                "chunk_id": chunk["chunk_id"],
                "page": page,
                "text": text,
                "sha256": sha256_text(f"{doc_id}::{text}"),
                "company": "Headlam Group Plc",
                "year": 2025,
            }
        )

    TASK_BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(BRONZE_TASK_PATH, index=False)

    BRONZE_GLOBAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(BRONZE_GLOBAL_PATH, index=False)

    if update_manifest:
        _update_task_manifest(pdf_sha, BRONZE_TASK_PATH)
        _update_companies_manifest(BRONZE_GLOBAL_PATH)

    return BRONZE_TASK_PATH


def _update_task_manifest(pdf_sha: str, bronze_path: Path) -> None:
    manifest = {
        "doc_id": "headlam-sustainability-2025",
        "company": "Headlam Group Plc",
        "year": 2025,
        "pdf_path": str(PDF_PATH),
        "pdf_sha256": pdf_sha,
        "bronze_path": str(bronze_path),
        "last_ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _update_companies_manifest(bronze_path: Path) -> None:
    COMPANIES_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    if COMPANIES_MANIFEST.exists():
        data = json.loads(COMPANIES_MANIFEST.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = []
    else:
        data = []

    entry = {
        "company": "Headlam Group Plc",
        "year": 2025,
        "slug": "headlam-group-plc",
        "bronze": str(bronze_path),
        "sources": {"pdf": str(PDF_PATH)},
    }

    updated = False
    for index, existing in enumerate(data):
        if existing.get("company") == entry["company"] and existing.get("year") == entry["year"]:
            data[index] = entry
            updated = True
            break
    if not updated:
        data.append(entry)

    COMPANIES_MANIFEST.write_text(json.dumps(data, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic bronze data for Headlam 2025.")
    parser.add_argument("--skip-manifest", action="store_true", help="Do not update manifests.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_bronze(update_manifest=not args.skip_manifest)
    print(json.dumps({"status": "ok", "bronze_path": str(BRONZE_TASK_PATH)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
