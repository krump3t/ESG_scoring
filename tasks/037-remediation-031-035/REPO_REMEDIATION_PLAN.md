# Task 037 Repository Remediation Plan – Zero-Ambiguity Hand-Off

**Objective:** Fully remediate the systemic issues identified in the 2025-11-05 codebase, execute the Docling migration, and restore validation gates to PASS under SCA v13.8-MEA. This plan is prescriptive; follow each step in order and capture evidence after every phase.

---

## Phase 0 – Preparation (No Code Changes)
1. Ensure you are on branch `remediation/sonnet-tasks-031-035` (or create a new feature branch off it).
2. From repository root (`C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine`), run the current validation baseline:
   ```bash
   python3 tasks/037-remediation-031-035/EXECUTION_PLAN.md  # follow V0–V10 instructions manually
   ```
   *Expected:* V0 PASS_WITH_WARNINGS, V1 PASS, V2 FAIL (static hygiene), V3 PASS, rest PENDING. Capture artefacts in `tasks/037-remediation-031-035/artifacts/diagnostics/`.

3. Archive the baseline status file (do not overwrite) for comparison:
   ```bash
   copy tasks\037-remediation-031-035\artifacts\diagnostics\STATUS.json tasks\037-remediation-031-035\artifacts\diagnostics\STATUS_BASELINE_20251105.json
   ```

---

## Phase 1 – Docling Migration (Highest Priority)
Goal: Remove PyMuPDF usage, make Docling the sole ingestion backend, and align tests.

1. **Dependencies**
   - Confirm `docling>=2.6.0`, `docling-core`, `docling-parse`, `docling-ibm-models` are present in `requirements.txt`. (Already true, just re-verify.)
   - Remove `PyMuPDF` from `requirements.txt` and any other requirement files (`requirements.api.txt`, lockfiles). Regenerate lock file via `pip freeze` and `pip-audit` once code changes are complete (Phase 5).

2. **Ingestion Refactor**
   - Replace `libs/ingestion/pdf_parser.py` with a Docling-based parser:
     - Use `DoclingBackend` to produce structured results.
     - Preserve fields expected by downstream code (doc_id, page_count, metadata).
     - Remove all `fitz` imports.
   - Delete or deprecate modules that exclusively wrap PyMuPDF (`libs/extraction/backend_default.py`) or convert them into Docling adapters.

3. **Chunker Refactor**
   - Modify `libs/chunking/structure_aware_chunker.py` to consume Docling pages/metadata.
   - Ensure chunk metadata includes `section_title`, `chunk_type`, `char_start`, `char_end` (map to Docling offsets—if not provided, set 0 consistently).
   - Update CLI (`scripts/chunk_cli.py`) to call the new Docling pipeline.

4. **Parser Backend Wiring**
   - Update `libs/extraction/parser_backend.py` so Docling is the default backend.
   - Remove PyMuPDF feature toggles from configs (`configs/pdf_backend.json` should list `"docling"` only unless a legacy fallback is intentionally retained with a loud warning).

5. **Scripts & Utilities**
   - Replace PyMuPDF usage in helper scripts (`scripts/pdf_to_silver.py`, `scripts/create_test_bronze_data.py`, ingestion utilities) with Docling equivalents.
   - Ensure scripts fail gracefully if Docling models are missing but emit clear install instructions.

6. **Tests & Fixtures**
   - Update CP tests (`tests/cp/test_structure_aware_chunker_037.py`, etc.) to validate Docling behaviour.
   - Regenerate fixtures, parquet outputs, or mocks based on Docling output.
   - Remove or refactor PyMuPDF-only tests (e.g., skip or delete tests that require fitz).

7. **Verification**
   - Run targeted unit tests for Docling components:
     ```bash
     pytest tests/cp/test_structure_aware_chunker_037.py -v
     pytest tests/cp/test_backend_docling.py -v
     ```
   - Document any intentionally skipped tests in `tasks/037-remediation-031-035/reports/DOCLING_MIGRATION_NOTES.md`.

Deliverable: Docling-only ingestion path with tests passing locally (even if coverage gate is not yet rerun).

---

## Phase 2 – Static Hygiene Remediation (Failing Gate V2)
Goal: Reduce lint/type violations in critical scope to meet SCA standard (≤10 lint issues, 0 mypy errors in targeted modules).

1. **Define Scope**
   - Primary CP modules: `libs/extraction/backend_docling.py`, `libs/chunking/structure_aware_chunker.py`, `agents/retrieval/hybrid_retriever.py`, `agents/orchestration/langgraph_orchestrator.py`, `libs/ingestion/pdf_parser.py`, Docling-related scripts/tests.
   - Secondary high-risk modules: `scripts/run_e2e_cold_start.py`, `apps/pipeline/demo_flow.py`, `apps/evaluation/response_quality.py` (break down responsibilities, extract helper modules).

2. **Lint Fixes**
   - Address top error classes from the baseline ruff report (E501 long lines, E402 late imports, F821 undefined names, C901 complexity, E722 bare `except`, F841 unused locals).
   - Configure ruff to use per-package ignores only where justified; prefer code fixes.

3. **Type Fixes**
   - Resolve the 113 mypy errors, starting with CP/Docling modules. Add type annotations, install stubs, or refactor code for clarity.
   - For global missing stubs (e.g., docling), provide local `.pyi` stubs if official types are unavailable.

4. **Refactor Large Modules (address “god-class” smell)**
   - Split `scripts/run_e2e_cold_start.py`, `apps/pipeline/demo_flow.py`, and `apps/evaluation/response_quality.py` into smaller, focused modules. Ensure new modules have unit tests and static typing.
   - Avoid new abstraction errors: keep domain-specific logic local; do not over-generalize identical-looking code without verifying shared intent.

5. **Re-run static analysis on scoped modules first:**
   ```bash
   ruff check libs/extraction/backend_docling.py libs/chunking/structure_aware_chunker.py agents/retrieval/hybrid_retriever.py agents/orchestration/langgraph_orchestrator.py --fix
   mypy libs/extraction/backend_docling.py libs/chunking/structure_aware_chunker.py agents/retrieval/hybrid_retriever.py agents/orchestration/langgraph_orchestrator.py
   ```
   Once clean, expand to the rest of the repository; document any residual issues that require separate tasks.

Deliverable: `tasks/037-remediation-031-035/artifacts/diagnostics/ruff.txt` and `mypy.txt` showing ≤10 lint warnings (in total) and 0 mypy errors for targeted modules. Update `STATUS.json` after rerun.

---

## Phase 3 – Digital Exhaust & Technical Debt Cleanup
Goal: Remove unmanaged TODO/FIXME and replace with tickets or implemented code; document managed debt.

1. **TODO Sweep**
   - Search the repo for `TODO`, `FIXME`, `NotImplementedError`, and commented-out blocks (`rg -n "TODO|FIXME|NotImplemented"`, `rg -n "^\s*#\s*"`).
   - For each item:
     - Implement the functionality if feasible (preferred), or
     - Create a tracked ticket and convert the comment to `TODO(TICKET-123)`, or
     - Remove/commented code entirely if obsolete (version control retains history).
   - Pay special attention to gating TODOs (e.g., `agents/orchestration/langgraph_orchestrator.py:213`). These must be implemented or tracked explicitly.

2. **Update Documentation**
   - If tickets are created, reference them in `tasks/037-remediation-031-035/context/claims_index.json` exclusions or in `REMEDIATION_SUMMARY.md`.

Deliverable: TODO scan returns only managed debt (ticket references) or explanatory comments. Update `tasks/037-remediation-031-035/reports/DIGITAL_EXHAUST_AUDIT.md` summarizing actions.

---

## Phase 4 – Dependency & Configuration Integrity
Goal: align runtime dependencies, lockfiles, and configuration with the new Docling stack; remove conflicting packages.

1. **Dependencies**
   - After Phase 1–3 code changes, regenerate `requirements.lock` using the repo’s preferred method (e.g., `pip freeze` into `tasks/037-remediation-031-035/artifacts/diagnostics/requirements.lock`). Ensure only required packages remain; remove duplicates.
   - Run `pip-audit -f json -o tasks/037-remediation-031-035/artifacts/diagnostics/pip_audit.json`. Resolve all vulnerabilities (upgrade packages or document accepted risk with justification; eight known issues must be addressed).

2. **Environment Drift**
   - Document Docling-specific environment variables (`DOCLING_DISABLE_GPU`, etc.) in `.env.template` with descriptions.
   - Update onboarding/README instructions to use the new ingestion pipeline (Docling). Remove PyMuPDF references.

3. **CI Alignment**
   - Ensure CI workflows install Docling dependencies (wheel + models) and do NOT install PyMuPDF.
   - Add a CI job to run the validation plan’s V0–V2 subset (lint, mypy, pip-audit) on each PR touching CP modules.

Deliverable: Updated `requirements.lock`, `pip_audit.json` with zero unresolved vulnerabilities, README/onboarding docs quoting Docling steps.

---

## Phase 5 – Validation & Documentation Close-Out
Goal: Re-run full validation, confirm all gates pass, and record results.

1. Execute the complete validation plan (`EXECUTION_PLAN.md`) after all remediation steps:
   - V0–V10 must pass (no FAIL or WARN). PENDING statuses should become PASS or SKIP with justification (only allowed for external-service dependent gates).

2. Update Artefacts:
   - `tasks/037-remediation-031-035/artifacts/diagnostics/STATUS.json` (new timestamp, all PASS)
   - `validation_report_037.json` summarizing results
   - Coverage report (`coverage_037.xml`) showing ≥95 % in CP modules
   - Determinism evidence (`determinism_report.json`) with matching hashes

3. Claims & Documentation:
   - Set claims C001 & C002 status to “verified” in `claims_index.json`
   - Update `REMEDIATION_SUMMARY.md` status to “Docling migration complete – awaiting Task 036”
   - Add final notes to `DOCLING_MIGRATION_PLAN.md` documenting completion and residual risks (if any)

4. Git Hygiene:
   - Ensure `git status` shows only intentional changes; commit with a descriptive message, e.g., `feat: migrate ingestion to docling and restore validation gates`.

---

## Phase 6 – Post-Migration Follow-Up (Optional, but recommended)
1. **Resilience (Task 036) Kickoff:** Prepare a separate plan for resilience infrastructure after this remediation is merged.
2. **Automation Enhancements:** Add pre-commit hooks (ruff, mypy, pip-audit) obligatory for CP modules.
3. **Security Review:** Engage AppSec tools to catch AI-induced vulnerabilities highlighted in the systemic report.

---

## Success Criteria Checklist
- [ ] Docling-only ingestion (no PyMuPDF references in code/tests/requirements)
- [ ] Ruff/mypy clean for CP modules (≤10 lint warnings, 0 type errors)
- [ ] TODO/FIXME stubs removed or ticketed
- [ ] Pip-audit clean (0 unresolved CVEs)
- [ ] V0–V10 validation gates PASS
- [ ] Claims C001/C002 marked verified; documentation updated
- [ ] Final STATUS.json reflects PASS across all hard gates

---

**Final Instruction:** Do not skip validation stages or gate fixes. All remediation must be evidence-backed, with artefacts stored under `tasks/037-remediation-031-035/artifacts/`. If a step cannot be completed, document the blocker in `reports/BLOCKERS.md` with proposed mitigation.*** End Patch
