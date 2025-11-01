# Initial Findings — SCA v13.8

This document consolidates the initial authenticity and compliance findings, aligned to Full Protocol v13.8. It summarizes violations, adds CP‑critical gaps not covered by the default detectors, and links to the canonical machine‑readable and human reports for the complete, line‑by‑line violation list.

Generated: 2025-10-27
Protocol Reference: `full_protocol.md` (v13.8)

---

## Summary

- Total violations: 77
- Severity: 0 fatal, 77 warn
- Detectors run: 8
- Canonical artifacts
  - Human: `artifacts/authenticity/report.md`
  - JSON: `artifacts/authenticity/report.json`

Note: The JSON and Markdown reports contain the full, enumerated list of every violation with `file:line`, violation type, description, and code snippet. This file adds contextual analysis and CP‑critical issues.

---

## Violations by Category (Highlights)

The full list of all items for each category is in `artifacts/authenticity/report.md` and `report.json`.

### 1) JSON-as-Parquet Misuse (16 WARN)

- Production examples:
  - `agents/scoring/rubric_models.py:183`
  - `apps/mcp_server/server.py:30`
  - `rubrics/archive/compile_rubric.py:4`, `:20`
- Tests and audit testing demonstrate detection coverage (multiple entries in `tests/…`).

Remediation: Replace `to_json()` with `to_parquet()` for data artifacts; dual-write or reader adapters during transition.

### 2) Network Imports in Production/Scripts (34 WARN)

- Direct `requests` imports across agents and ingestion:
  - `agents/crawler/data_providers/{cdp,gri,sasb,sec_edgar,ticker_lookup}.py`
  - `agents/crawler/sustainability_reports_crawler.py`
  - `apps/ingestion/{parser.py,crawler.py,report_fetcher.py}`
  - `infrastructure/health/check_all.py`
- Several scripts/tests import `requests` as part of integration checks.

Remediation: In CP scope, encapsulate via `libs/utils/http_client.py` and inject `HTTPClient`; tests should use `MockHTTPClient`.

### 3) Nondeterministic Time Usage (12 WARN)

- Primarily in task QA and test scaffolds:
  - `tasks/006-multi-source-ingestion/qa/phase1_integration_test.py` (multiple lines)
  - `tasks/007-tier2-data-providers/qa/phase2_integration_test.py` (multiple lines)
  - `tests/infrastructure/conftest.py` (multiple lines)

Remediation: Use `libs/utils/clock.get_clock().time()/now()` with FIXED_TIME in tests.

### 4) Silent Exception Handling (15 WARN)

- Production examples:
  - `apps/api/main.py:259`
  - `apps/integration_validator.py:110/188/278/327`
  - `libs/utils/determinism.py:89`
- Scripts and tests also include silent blocks.

Remediation: Replace with logging + re-raise or explicit error returns. Add failure-path tests.

---

## CP‑Critical Gaps (Not Fully Covered by Detectors)

- CP stub/constant return without `# @allow-const`:
  - `apps/scoring/scorer.py:33` returns hard-coded stage/confidence.
- Placeholder scoring logic in CP retrieval:
  - `libs/retrieval/semantic_retriever.py:151` placeholder score contribution.
- Direct wall‑clock in CP scope:
  - `libs/retrieval/semantic_retriever.py:165`, `:192` use `datetime.now(...)`.

Impact: Violates `authenticity_ast` and `placeholders_cp` expectations; affects determinism unless guarded and tested.

Remediation: Implement real logic or guard with `# @allow-const:<reason>` plus varied-input tests; switch to `get_clock()`.

---

## Dependency Hygiene Findings

- Unpinned or loosely pinned dependencies (examples):
  - `requirements.txt`: `ibm-watsonx-ai>=0.2.0`, `cassandra-driver>=3.28.0`, `duckdb>=0.9.2`, `redis>=5.0.0`, `psycopg2-binary>=2.9.0`, `pyngrok>=6.0.0`, `pytest>=7.4.0`, `pytest-cov>=4.1.0`, `hypothesis>=6.88.0`.
  - `requirements-dev.txt`: `duckdb>=0.9.2`, unpinned `beautifulsoup4`, `lxml`, `playwright`, `numpy`; several `pytest*` and `mypy/ruff` with `>=`.
  - `requirements-runtime.txt`: `duckdb>=0.9.2`.
- Missing `requests` in requirements despite widespread usage.

Remediation: Pin all non-exempt packages with `==`; add `requests==<pin>`; optionally generate `requirements.lock`.

---

## Protocol & Runner Gaps vs v13.8

- `.sca_config.json` lists `protocol_version: "12.2"` — should be `"13.8"` with additional keys per §8.
- Missing `validators/placeholders_cp.py`; runner lacks many gates and `validate review` subcommand.
- `scripts/qa/authenticity_audit.py` determinism test path returns placeholder PASS — needs implementation.
- Conflicting compliance artifacts: `tasks/COMPLIANCE_REPORT.json` vs `tasks/validation_report.json`; violates honest status reporting §11.

Remediation: Update config, implement validator and review gate, complete determinism proof, reconcile reports.

---

## Full Violation List

The complete, enumerated list of all violations (every file:line, type, severity, description, and code snippet) is provided in:

- `artifacts/authenticity/report.md` (human-readable)
- `artifacts/authenticity/report.json` (machine-readable)

Use these as the canonical source for line-by-line verification. This file adds prioritization and remediation context to guide execution.

