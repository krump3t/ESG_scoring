# Task 037 Remediation – Validation & Fix Plan (v4.0)

**Task ID:** 037-remediation-031-035  
**Last Updated:** 2025-11-04  
**Primary Goal:** Validate the current state of Tasks 031‑035 deliverables with zero code changes, then execute targeted fixes only when validation exposes gaps.  
**Operating Modes:**  
- **Phase V – Validation (read-only):** gather evidence, fail closed on hard gates, no edits.  
- **Phase R – Remediation (write):** apply fixes selected from validation findings, then rerun the affected validation gates.

---

## 0. Gate Summary

| Gate | Validation Step | Type | Notes |
|------|-----------------|------|-------|
| Env snapshot + pip-audit | V0 | Hard | pip-audit may be skipped if unavailable (record reason). |
| Toolchain check (`ruff`, `mypy`, `pytest`, `bandit`, `detect-secrets`, `pip-audit`) | V1 | Hard | No installs; fail if missing. |
| Static hygiene (`ruff`, `mypy`) | V2 | Hard | Scope every existing source directory (`agents`, `libs`, `apps`, `src`). |
| Config & doc reconciliation (incl. Task 036 status) | V3 | Hard | Report mismatches; no auto edits. |
| Implementation smoke tests | V4 | Soft | Capture actual behavior (pass/fail) in logs. |
| Targeted pytest coverage (≥95 % CP modules) | V5 | Hard | Focus on CP files (`hybrid_retriever`, `structure_aware_chunker`, `rrf_fusion`). |
| Parity & determinism | V6 | Hard when artifacts exist; otherwise SKIP with rationale. |
| Schema/vector dimension | V7 | Soft | SKIP acceptable when Astra unavailable (record reason). |
| TODO / digital-exhaust audit | V8 | Soft | Surface unmanaged TODOs, commented stubs. |
| Security scans (bandit / detect-secrets) | V9 | Soft | Advisory; promote findings to remediation backlog. |
| Status synthesis (`STATUS.json`) | V10 | Informational | Must capture PASS/FAIL/SKIP per gate. |

Remediation gates (Phase R) are opt-in; run only after sign-off on validation outcomes.

---

## Phase V – Validation (No Code Changes)

> **Important:** run these steps exactly as written. Do not edit source, requirements, or manifests during Phase V. All commands execute from the repo root  
> `C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine`.

### V0. Environment Snapshot & Dependency Scan (Hard Gate)
1. `pip freeze > artifacts/diagnostics/requirements.lock`
2. Run `pip-audit -r artifacts/diagnostics/requirements.lock -f json --output artifacts/diagnostics/pip_audit.json`
3. Record Python version and platform in `artifacts/diagnostics/env_snapshot.json`
4. **Fail condition:** pip-audit reports unresolved vulnerabilities (unless the tool is missing → record SKIP with explanation).

### V1. Toolchain Verification (Hard Gate)
1. Ensure these tools resolve via PATH or the active venv: `ruff`, `mypy`, `pytest`, `bandit`, `detect-secrets`, `pip-audit`
2. Write results to `artifacts/diagnostics/toolchain_verification.json`
3. **Fail condition:** any tool missing (no installs during validation).

### V2. Static Hygiene (Hard Gate)
1. Identify existing source directories among `agents`, `libs`, `apps`, `src`
2. Run `ruff check <dirs> --select I,F,N,E,W,C901,UP --fix` (non-zero exit fails the gate)
3. Run `mypy --strict <dirs>`
4. Store outputs in `artifacts/diagnostics/ruff.txt` and `artifacts/diagnostics/mypy.txt`

### V3. Configuration, Documentation & Status Reconciliation (Hard Gate)
1. Confirm presence of key artefacts:
   - `agents/retrieval/hybrid_retriever.py`
   - `agents/orchestration/langgraph_orchestrator.py`
   - `libs/chunking/structure_aware_chunker.py`
   - `libs/fusion/rrf_fusion.py`
   - `libs/retrieval/bm25_search.py`
   - `libs/retrieval/vector_search_astra.py`
   - `agents/scoring/rubric_v3_scorer.py`
   - `agents/scoring/parity_validator.py`
   - `.env.template`
   - `rubrics/esg_rubric_schema_v3.json`
   - `tasks/036-resilience-performance-e2e/context/cp_paths.json` & related status docs
2. Validate `.env.template` contains mandatory keys (`ASTRA_DB_API_ENDPOINT`, `ASTRA_DB_APPLICATION_TOKEN`, `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_MODEL_ID`, `EMBED_MODEL`)
3. Attempt to `model_validate` the rubric schema via `ScoringRubric` (record SKIP if imports fail but JSON is valid)
4. Detect discrepancies where Task 036 is marked “DEFERRED” in manifests yet “complete” in reports
5. Output `artifacts/diagnostics/doc_impl_reconciliation.json`
6. **Fail condition:** missing artefacts, invalid template, invalid schema, or unresolved Task 036 discrepancy

### V4. Implementation Smoke Tests (Soft Gate – Observational)
- **Chunker CLI**  
  `python scripts/chunk_cli.py --input data/raw/LSE_HEAD_2025.pdf --output artifacts/diagnostics/chunker_probe.parquet --method structure`  
  Expectation today: failure due to missing `char_start`/`char_end`. Capture every run (stdout/stderr) in `artifacts/diagnostics/chunker_cli.log`.
- **Hybrid CLI (BM25 only)**  
  `python scripts/hybrid_cli.py --mode bm25 --query "ESG metrics" --chunks artifacts/diagnostics/chunker_probe.parquet --out artifacts/diagnostics/hybrid_bm25_probe.json`  
  If chunker output is missing, log dependency failure; do not edit code to “fix” it during validation.
- Record actual behavior for remediation triage.

### V5. Targeted Pytest Coverage (Hard Gate)
1. Run `pytest` for:
   - `tests/cp/test_hybrid_retriever_037.py`
   - `tests/cp/test_structure_aware_chunker.py`
   - `tests/cp/test_langgraph_orchestrator.py`
2. Apply coverage to:
   - `agents.retrieval.hybrid_retriever`
   - `libs.chunking.structure_aware_chunker`
   - `libs.fusion.rrf_fusion`
3. Enforce `--cov-branch --cov-fail-under=95`
4. Save XML report to `artifacts/diagnostics/coverage_037.xml` and summary to `coverage_037.txt`
5. **Fail condition:** pytest failure or coverage < 95 % for targeted modules

### V6. Parity & Determinism Validation (Hard Gate where artefacts exist)
1. Ensure baseline inputs exist (regenerate BM25 outputs if necessary; document SKIP if inputs unavailable)
2. Run parity validator:  
   `python -m agents.scoring.parity_validator --topk <topk.json> --evidence <evidence.json> --out artifacts/demo/parity.json`
3. Determinism:
   - Hash current scoring, evidence, maturity outputs  
   - Re-run scorer with `PYTHONHASHSEED=0`, `SEED=42`  
   - Compare hashes; write `artifacts/diagnostics/determinism_report.json`
4. **Fail condition:** parity CLI error or hash mismatch

### V7. Schema / Vector Dimension Check (Soft Gate)
1. Attempt `from libs.vectors.astra_schema_check import describe_collection`
2. Query the `chunks` collection; compare `embedding_dimension` with `EMBED_MODEL`
3. Record result (`PASS` / `FAIL` / `SKIP`) in `artifacts/diagnostics/schema_vector_check.json`
4. External connection issues → mark `status: "SKIP"` with reason

### V8. TODO / “Digital Exhaust” Audit (Soft Gate)
1. Suggested commands:  
   - `rg -n "TODO|FIXME" --hidden --glob '!.git/*'`  
   - `rg -n "Mock\(" tests/cp`  
   - `rg -n "pass\s*#\s*stub"`
2. Classify findings: ticketed TODO, orphan TODO, commented-out code, legacy stubs
3. Summarize in `artifacts/diagnostics/digital_exhaust_summary.txt`

### V9. Security Scans (Soft Gate – Advisory)
1. `bandit -q -r <dirs> -f json -o artifacts/diagnostics/security_bandit.json`
2. `detect-secrets scan --all-files --json > artifacts/diagnostics/secrets_scan.json`
3. Highlight high-severity issues for remediation backlog; do not fail validation automatically

### V10. Status Synthesis
1. Aggregate gate results into `artifacts/diagnostics/STATUS.json`, marking `PASS`, `FAIL`, or `SKIP (reason)`
2. Produce analyst summary `artifacts/diagnostics/validation_report_037.json`, explicitly citing:
   - Chunker CLI failure (expected)
   - Missing runtime dependencies (`astrapy`, `langgraph`, etc.)
   - Task 036 completion/documentation mismatch
   - Any CVEs, secrets, or TODO clusters requiring remediation
3. Hold a review before entering Phase R

---

## Phase R – Remediation (Apply Only After Validation Review)

Execute remediation steps only for confirmed deficiencies. After each fix, rerun the relevant validation gates.

### R1. Chunker Dataclass Fix
- Add missing metadata fields (e.g., `char_start: int = 0`, `char_end: int = 0`) to the `Chunk` dataclass and ensure CLI serialization writes them
- Rerun V4 (smoke test) and V5 (coverage) to confirm the fix

### R2. Dependency Specification
- Add/pin missing runtime dependencies to `requirements.txt` / lock files (`astrapy`, `langgraph`, `PyMuPDF`, `duckdb`, `sentence-transformers`)
- Install locally; rerun V0 (freeze + pip-audit) and V1 toolchain gate
- Resolve any vulnerabilities reported by pip-audit

### R3. Task 036 Alignment
- Update Task 036 manifests/context to reflect true status (deferred or completed)
- Ensure reports and validation docs reflect the same state
- Rerun V3 to confirm alignment

### R4. Additional Hardening
- Triage TODO/digital-exhaust findings (create tickets or remove noise), then rerun V8 summary
- Increase coverage for any modules flagged in V5 gaps; rerun the gate
- Address security findings (rotate secrets, refactor risky patterns) and rerun V9

### R5. Remediation Close-out
- After finishing fixes, rerun the affected validation gates (e.g., V0–V6 after code/dep changes)
- Update `artifacts/diagnostics/STATUS.json` with new timestamp and final PASS/FAIL
- Document remaining follow-up actions in `artifacts/diagnostics/remediation_notes.txt`

---

## Deliverables Checklist

| Phase | Artifact | Description |
|-------|----------|-------------|
| V0–V10 | `artifacts/diagnostics/*` | Complete evidence set (freeze, audits, logs, coverage, reports) |
| V4 | `artifacts/diagnostics/chunker_cli.log`, `hybrid_bm25_probe.json` | Actual runtime outputs (pass/fail) |
| V5 | `coverage_037.xml`, `coverage_037.txt` | Proof of ≥ 95 % coverage for CP modules |
| V6 | `artifacts/demo/parity.json`, `determinism_report.json` | Determinism/parity validation |
| V8 | `digital_exhaust_summary.txt` | TODO/comment audit |
| V9 | `security_bandit.json`, `secrets_scan.json` | Security scan summaries |
| V10 | `STATUS.json`, `validation_report_037.json` | Validation summary and gate status |
| R-phase | `remediation_notes.txt` | Fixes applied and rerun gates |

---

## Notes & Known Constraints

- **PDF path:** use `data/raw/LSE_HEAD_2025.pdf`. The string `LSE_HEADLAM_2025.pdf` is incorrect and will throw `FileNotFoundError`.  
- **External services:** Vector/Astra checks require valid credentials. Without them, log `SKIP` with a clear reason—do not mock.  
- **AI risk shift:** keep remediation changes small and security-focused; highlight sensitive areas during human review.  
- **Secrets handling:** never commit credentials. If detect-secrets finds exposures, rotate and document remediation.  
- **Environment drift:** treat `requirements.lock` outputs as disposable snapshots. Regenerate after dependency fixes to avoid “works on my machine” issues.

---

Following this split-phase plan preserves an auditable validation record, makes systemic issues visible, and ensures remediation changes remain deliberate, minimal, and fully verifiable.
