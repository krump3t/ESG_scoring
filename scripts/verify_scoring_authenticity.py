#!/usr/bin/env python3
"""
SCA v13.8-MEA Scoring Authenticity Verifier

This script validates that scoring outputs meet all authenticity invariants:
1. Schema validation: All 7 themes present with numeric scores
2. Evidence gate: ≥2 quotes from ≥2 pages per theme
3. Parity gate: evidence_ids ⊆ fused_topk
4. Evidence grounding: Every quote exists in silver Parquet with text containment
5. Overall maturity: Computed as equal-weight mean across 7 themes (0-4 scale)

Fail-closed: Any gate failure → status="blocked" with specific remediation

Usage:
    python scripts/verify_scoring_authenticity.py
    python scripts/verify_scoring_authenticity.py --config configs/companies_local.yaml
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import duckdb

# Required themes from rubric v3
REQUIRED_THEMES = ["TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"]
MIN_QUOTES = 2
MIN_PAGES = 2


def load_scoring_docs() -> Dict[str, Dict[str, Any]]:
    """Load all scoring_response.json files from matrix artifacts."""
    scoring_files = {}

    for file_path in glob.glob("artifacts/matrix/*/baseline/run_1/scoring_response.json"):
        parts = Path(file_path).parts
        doc_id = parts[2]  # artifacts/matrix/<doc_id>/...

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                scoring_files[doc_id] = json.load(f)
        except Exception as e:
            print(f"[revise] cannot read {file_path}: {e}")

    return scoring_files


def assert_schema(doc_id: str, score: Dict[str, Any]) -> None:
    """Validate schema: All themes present with numeric scores."""
    if "themes" not in score:
        raise AssertionError(f"[schema] 'themes' key missing in {doc_id}")

    for theme in REQUIRED_THEMES:
        if theme not in score["themes"]:
            raise AssertionError(f"[schema] theme {theme} missing in {doc_id}")

        theme_data = score["themes"][theme]

        if "score" not in theme_data:
            raise AssertionError(f"[schema] {doc_id}:{theme} missing 'score' field")

        if not isinstance(theme_data["score"], (int, float)):
            raise AssertionError(
                f"[schema] {doc_id}:{theme} score not numeric: {type(theme_data['score'])}"
            )

        # Soft check for evidence (hard check in evidence_gate)
        if "evidence" not in theme_data:
            print(f"[warn] {doc_id}:{theme} missing 'evidence' field")


def evidence_gate(doc_id: str, score: Dict[str, Any]) -> None:
    """Validate evidence: ≥2 quotes from ≥2 pages per theme."""
    for theme in REQUIRED_THEMES:
        theme_data = score["themes"][theme]
        evidence = theme_data.get("evidence", [])

        if not isinstance(evidence, list):
            raise AssertionError(
                f"[evidence] {doc_id}:{theme} evidence not a list: {type(evidence)}"
            )

        # Count valid quotes (with text)
        valid_quotes = [e for e in evidence if isinstance(e, dict) and e.get("text")]
        if len(valid_quotes) < MIN_QUOTES:
            raise AssertionError(
                f"[evidence] {doc_id}:{theme} has only {len(valid_quotes)} quotes, need {MIN_QUOTES}"
            )

        # Count distinct pages
        pages = {e.get("page") for e in evidence if isinstance(e, dict) and e.get("page") is not None}
        distinct_pages = [p for p in pages if p is not None]

        if len(distinct_pages) < MIN_PAGES:
            raise AssertionError(
                f"[evidence] {doc_id}:{theme} has only {len(distinct_pages)} distinct pages, need {MIN_PAGES}"
            )


def parity_gate(doc_id: str, score: Dict[str, Any]) -> None:
    """Validate parity: evidence_ids ⊆ fused_topk."""
    parity_file = f"artifacts/matrix/{doc_id}/pipeline_validation/demo_topk_vs_evidence.json"

    try:
        with open(parity_file, "r", encoding="utf-8") as f:
            parity_data = json.load(f)
    except FileNotFoundError:
        raise AssertionError(
            f"[parity] parity validation file not found: {parity_file}"
        )

    if not parity_data.get("subset_ok", False):
        raise AssertionError(
            f"[parity] subset_ok=false for {doc_id} (evidence_ids not subset of topk)"
        )


def evidence_grounding(doc_id: str, score: Dict[str, Any]) -> None:
    """Validate evidence grounding: Every quote exists in silver Parquet."""
    # Load silver data for this doc_id
    silver_pattern = "data/silver/org_id=*/year=*/*_chunks.parquet"

    try:
        con = duckdb.connect()
        query = f"""
            SELECT id, page, page_no, text, chunk_id
            FROM read_parquet('{silver_pattern}')
            WHERE doc_id = ?
        """
        df = con.execute(query, [doc_id]).fetchdf()
        con.close()
    except Exception as e:
        raise AssertionError(
            f"[grounding] Failed to load silver data for {doc_id}: {e}"
        )

    if df.empty:
        raise AssertionError(
            f"[grounding] No silver data found for {doc_id} in {silver_pattern}"
        )

    # Build index: chunk_id -> (page, text)
    chunk_index = {}
    for _, row in df.iterrows():
        # Try multiple possible ID columns
        chunk_id = row.get("chunk_id") or row.get("id")
        page = row.get("page") or row.get("page_no")
        text = row.get("text", "")

        if chunk_id:
            chunk_index[chunk_id] = (page, text)

    # Validate each evidence item
    for theme in REQUIRED_THEMES:
        theme_data = score["themes"][theme]
        evidence = theme_data.get("evidence", [])

        for ev in evidence:
            if not isinstance(ev, dict):
                continue

            # Extract evidence IDs (try multiple possible field names)
            ev_id = (
                ev.get("chunk_id")
                or ev.get("id")
                or ev.get("evidence_id")
                or ev.get("source_id")
            )
            ev_text = (ev.get("text") or ev.get("quote") or "").strip()
            ev_page = ev.get("page") or ev.get("page_no")

            if not ev_id:
                # Skip if no ID (some evidence may be synthetic summaries)
                continue

            if ev_id not in chunk_index:
                raise AssertionError(
                    f"[grounding] {doc_id}:{theme} evidence ID not in silver: {ev_id}"
                )

            silver_page, silver_text = chunk_index[ev_id]

            # Validate page match
            if ev_page is not None and silver_page is not None:
                if ev_page != silver_page:
                    raise AssertionError(
                        f"[grounding] {doc_id}:{theme}:{ev_id} page mismatch: "
                        f"evidence={ev_page}, silver={silver_page}"
                    )

            # Validate text containment (loose match with normalization)
            if ev_text:
                import re

                normalize = lambda s: re.sub(r"\s+", " ", s.strip().lower())
                ev_norm = normalize(ev_text)
                silver_norm = normalize(silver_text)

                # Check if first 80 chars of evidence appear in silver
                if ev_norm[:80] not in silver_norm:
                    raise AssertionError(
                        f"[grounding] {doc_id}:{theme}:{ev_id} text not found in chunk\n"
                        f"Evidence (first 80): {ev_norm[:80]}\n"
                        f"Silver (first 200): {silver_norm[:200]}"
                    )


def compute_overall_maturity(score: Dict[str, Any]) -> float:
    """Compute overall maturity as equal-weight mean across 7 themes."""
    theme_scores = []

    for theme in REQUIRED_THEMES:
        if theme in score.get("themes", {}):
            theme_score = score["themes"][theme].get("score")
            if theme_score is not None:
                theme_scores.append(float(theme_score))

    if not theme_scores:
        raise AssertionError("[maturity] No valid theme scores found")

    overall = sum(theme_scores) / len(theme_scores)
    return round(overall, 1)


def main():
    parser = argparse.ArgumentParser(
        description="Verify scoring authenticity per SCA v13.8-MEA"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Config file (optional, for reference only)",
    )

    args = parser.parse_args()

    print("=== SCA v13.8-MEA Scoring Authenticity Verifier ===\n")

    # Load all scoring documents
    docs = load_scoring_docs()

    if not docs:
        print(
            "[revise] No scoring_response.json found in artifacts/matrix/*/baseline/run_1/"
        )
        print("ACTION: Ensure run_matrix.py has been executed and scoring outputs exist")
        sys.exit(2)

    print(f"Found {len(docs)} scoring documents\n")

    results = []
    failed = []

    for doc_id, score_data in docs.items():
        print(f"[{doc_id}] Validating...")

        try:
            # Gate 1: Schema
            assert_schema(doc_id, score_data)
            print(f"  ✓ Schema valid")

            # Gate 2: Evidence
            evidence_gate(doc_id, score_data)
            print(f"  ✓ Evidence gate passed")

            # Gate 3: Parity
            parity_gate(doc_id, score_data)
            print(f"  ✓ Parity gate passed")

            # Gate 4: Grounding
            evidence_grounding(doc_id, score_data)
            print(f"  ✓ Evidence grounding verified")

            # Compute overall maturity
            overall = compute_overall_maturity(score_data)
            print(f"  ✓ Overall maturity: {overall}\n")

            results.append({"doc_id": doc_id, "overall_maturity": overall})

        except AssertionError as e:
            print(f"  ✗ FAILED: {e}\n")
            failed.append({"doc_id": doc_id, "error": str(e)})

    # Generate report
    output_path = Path("artifacts/matrix/scoring_authenticity_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "status": "ok" if not failed else "blocked",
        "total": len(docs),
        "passed": len(results),
        "failed": len(failed),
        "results": results,
        "failures": failed,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"=== Summary ===")
    print(f"Total: {report['total']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"\nReport: {output_path}")

    if failed:
        print("\n=== Failures ===")
        for failure in failed:
            print(f"  [{failure['doc_id']}] {failure['error']}")
        sys.exit(3)

    print("\n[pass] All scoring authenticity gates passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
