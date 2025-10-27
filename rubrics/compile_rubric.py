#!/usr/bin/env python3
"""
Rubric Compiler: Idempotent MD→JSON converter for ESG Maturity Rubric v3.
Protocol: SCA v13.8-MEA | Deterministic | Local I/O only | No network

Input:  rubrics/esg_maturity_rubricv3.md (human-readable mirror)
Output: rubrics/maturity_v3.json (canonical source of truth)
Schema: rubrics/esg_rubric_schema_v3.json (validation target)

Execution:
    PYTHONHASHSEED=0 SEED=42 python rubrics/compile_rubric.py \
        --in rubrics/esg_maturity_rubricv3.md \
        --schema rubrics/esg_rubric_schema_v3.json \
        --out rubrics/maturity_v3.json \
        --manifest artifacts/rubric_compile/run_manifest.json

Determinism guarantees:
    - Stable JSON key ordering (sort_keys=True)
    - Fixed timestamp (ISO UTC)
    - No randomness, no network calls
    - Two runs → byte-identical output
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def parse_md_rubric(md_path: Path) -> Dict[str, Any]:
    """
    Parse ESG Maturity Rubric MD into structured JSON.

    Strategy:
    - Extract version from header
    - Parse 7 theme sections by regex
    - Extract stage tables (0-4) with descriptors and evidence
    - Preserve schema alignment with esg_rubric_schema_v3.json
    """
    content = md_path.read_text(encoding="utf-8")

    # Extract version
    version_match = re.search(r"#\s*ESG Maturity Scoring Rubric v([\d.]+)", content)
    version = version_match.group(1) if version_match else "3.0"

    # Theme definitions (order matters for determinism)
    themes_order = [
        ("TSP", "Target Setting & Planning"),
        ("OSP", "Operational Structure & Processes"),
        ("DM", "Data Maturity"),
        ("GHG", "GHG Accounting"),
        ("RD", "Reporting & Disclosure"),
        ("EI", "Energy Intelligence"),
        ("RMM", "Risk Management & Mitigation"),
    ]

    themes = []

    for code, name in themes_order:
        # Find theme section
        theme_pattern = rf"##\s*\d+\)\s*{re.escape(name)}\s*\({re.escape(code)}\)"
        theme_match = re.search(theme_pattern, content)

        if not theme_match:
            raise ValueError(f"Theme {code} not found in MD")

        # Extract intent
        intent_match = re.search(
            r"\*\*Intent:\*\*\s*([^\n]+)",
            content[theme_match.end():theme_match.end() + 500]
        )
        intent = intent_match.group(1).strip() if intent_match else f"Evaluate {name.lower()}."

        # Extract stage table rows
        stages = {}
        for stage_num in range(5):  # 0-4
            # Match table row: | **N** | descriptor | evidence |
            stage_pattern = rf"\|\s*\*\*{stage_num}\*\*\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"
            stage_match = re.search(stage_pattern, content[theme_match.start():])

            if stage_match:
                descriptor = stage_match.group(1).strip()
                evidence_raw = stage_match.group(2).strip()

                # Parse evidence examples (semicolon or period separated)
                evidence_examples = [
                    e.strip().rstrip('.')
                    for e in re.split(r'[;.]', evidence_raw)
                    if e.strip() and e.strip().lower() not in ['n/a', 'none']
                ]

                # Derive label from descriptor (first phrase or keyword)
                label_candidates = {
                    0: "No targets|None|Manual|Bills only|No framework|No formal",
                    1: "Foundational|Ad-hoc|Structured manual|Basic metering|Qualitative only|Partial framework",
                    2: "Quantified|Formalized|Partially automated|Complete S1/S2|ISSB/TCFD narrative|KPIs & projects|Defined taxonomy",
                    3: "Science-aligned|Integrated|Unified platform|Comprehensive|Cross-framework|Automated analytics|Quantified",
                    4: "Validated science-based|Embedded & audited|Automated & real-time|Reasonable assurance|Assured & digitally tagged|Forecast & optimization|Enterprise-integrated",
                }

                # Extract label from descriptor or use fallback
                label = descriptor.split('.')[0].strip()
                if len(label) > 40:  # Too long, use keyword
                    for keyword in label_candidates[stage_num].split('|'):
                        if keyword.lower() in descriptor.lower():
                            label = keyword
                            break

                stages[str(stage_num)] = {
                    "label": label,
                    "descriptor": descriptor,
                    "evidence_examples": evidence_examples,
                }

        themes.append({
            "code": code,
            "name": name,
            "intent": intent,
            "stages": stages,
        })

    # Build output structure matching schema
    # Use fixed timestamp for determinism (from schema reference)
    rubric = {
        "version": version,
        "updated_utc": "2025-10-22T03:21:40Z",
        "name": "ESG Maturity Scoring Rubric",
        "description": "Seven-theme ESG maturity rubric (0–4) aligned with ESG Doc; designed for MCP + Iceberg scoring agent.",
        "scale": {"min": 0, "max": 4, "step": 1},
        "themes": themes,
        "scoring_rules": {
            "evidence_min_per_stage_claim": 2,
            "freshness_months_penalty": {
                "months": 24,
                "confidence_delta": -0.1,
            },
            "negative_overrides": [
                {"condition": "auditor_findings_contradict_claims == true", "cap_stage": 2},
                {"condition": "assurance_failed == true", "cap_stage": 1},
            ],
            "confidence_guidance": [
                {"range": [0.2, 0.4], "label": "weak"},
                {"range": [0.5, 0.7], "label": "adequate"},
                {"range": [0.8, 1.0], "label": "strong"},
            ],
            "framework_signals": {
                "SBTi": {"tsp_min_stage": 3, "approved_sets_stage": 4},
                "ISSB_TCFD": {"rd_min_stage": 2, "assured_and_tagged_sets_stage": 4},
                "GHG_Protocol": {"ghg_min_stage": 3, "reasonable_assurance_sets_stage": 4},
                "CSRD_ESRS": {"rd_3_4_support": True},
            },
        },
        "output_contract": {
            "score_record": {
                "org_id": "string",
                "year": "int",
                "theme_code": "string",
                "stage": "int (0-4)",
                "confidence": "float (0.0-1.0)",
                "evidence_ids": "array<string>",
                "frameworks": "array<string>",
                "snapshot_id": "string",
                "doc_manifest_uri": "string",
            },
            "evidence_record": {
                "evidence_id": "string",
                "org_id": "string",
                "year": "int",
                "theme_code": "string",
                "doc_id": "string",
                "page_no": "int",
                "span_start": "int",
                "span_end": "int",
                "extract_30w": "string",
                "hash_sha256": "string",
                "snapshot_id": "string",
            },
        },
    }

    return rubric


def validate_against_schema(data: Dict[str, Any], schema_path: Path) -> List[str]:
    """
    Validate compiled JSON against schema.
    Returns list of validation errors (empty if valid).
    """
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = []

    # Basic structural checks (simplified jsonschema-like validation)
    if data.get("version") != schema.get("version"):
        errors.append(f"Version mismatch: {data.get('version')} != {schema.get('version')}")

    if len(data.get("themes", [])) != len(schema.get("themes", [])):
        errors.append(f"Theme count mismatch: {len(data.get('themes', []))} != {len(schema.get('themes', []))}")

    # Validate each theme has required fields
    for idx, theme in enumerate(data.get("themes", [])):
        if "code" not in theme or "name" not in theme or "stages" not in theme:
            errors.append(f"Theme {idx}: missing required fields")

        # Validate stages 0-4 exist
        stages = theme.get("stages", {})
        if set(stages.keys()) != {"0", "1", "2", "3", "4"}:
            errors.append(f"Theme {theme.get('code')}: invalid stages {list(stages.keys())}")

    return errors


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def write_manifest(
    manifest_path: Path,
    input_path: Path,
    output_path: Path,
    schema_path: Path,
    validation_errors: List[str],
    elapsed_ms: float,
) -> None:
    """Write run manifest with deterministic metadata."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "agent": "SCA",
        "protocol_version": "13.8",
        "tool": "compile_rubric.py",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "determinism": {
            "seed": int(os.getenv("SEED", "42")),
            "pythonhashseed": int(os.getenv("PYTHONHASHSEED", "0")),
        },
        "inputs": {
            "md_path": str(input_path),
            "md_sha256": compute_sha256(input_path),
            "schema_path": str(schema_path),
            "schema_sha256": compute_sha256(schema_path),
        },
        "outputs": {
            "json_path": str(output_path),
            "json_sha256": compute_sha256(output_path) if output_path.exists() else None,
        },
        "validation": {
            "status": "pass" if not validation_errors else "fail",
            "errors": validation_errors,
        },
        "performance": {
            "elapsed_ms": round(elapsed_ms, 2),
        },
    }

    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8"
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compile ESG rubric MD to JSON")
    parser.add_argument("--in", dest="input", required=True, help="Input MD file")
    parser.add_argument("--schema", required=True, help="Schema JSON for validation")
    parser.add_argument("--out", dest="output", required=True, help="Output JSON file")
    parser.add_argument("--manifest", required=True, help="Run manifest output path")

    args = parser.parse_args()

    input_path = Path(args.input)
    schema_path = Path(args.schema)
    output_path = Path(args.output)
    manifest_path = Path(args.manifest)

    # Verify inputs exist
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
        return 1

    # Parse MD
    start_time = datetime.now(timezone.utc)
    try:
        rubric_data = parse_md_rubric(input_path)
    except Exception as e:
        print(f"ERROR: Failed to parse MD: {e}", file=sys.stderr)
        return 1

    # Validate against schema
    validation_errors = validate_against_schema(rubric_data, schema_path)

    # Write JSON with deterministic formatting
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(rubric_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

    # Write manifest
    write_manifest(manifest_path, input_path, output_path, schema_path, validation_errors, elapsed_ms)

    if validation_errors:
        print(f"WARNING: Validation errors found:", file=sys.stderr)
        for error in validation_errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    print(f"[OK] Rubric compiled: {output_path}")
    print(f"[OK] SHA256: {compute_sha256(output_path)}")
    print(f"[OK] Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
