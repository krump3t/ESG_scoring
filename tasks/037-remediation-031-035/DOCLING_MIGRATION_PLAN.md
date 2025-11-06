# Docling-Only Ingestion Migration Plan (Task 037 Hand-Off)

**Goal:** Eliminate PyMuPDF usage from the ingestion/structure-aware chunking pipeline and standardize on Docling as the sole PDF parsing and chunking backend. This plan assumes the validation/remediation workflow outlined in `EXECUTION_PLAN.md (v4.0)` remains in effect—run the Validation phase, apply the remediation below, then rerun the targeted gates.

---

## Phase 0 – Prerequisites
1. **Run Validation (Phase V)** from `EXECUTION_PLAN.md` to capture current evidence (expect PyMuPDF still in use and chunker CLI failing without it).
2. Review validation artefacts: chunker logs, coverage reports, `STATUS.json`, doc reconciliation.
3. Obtain sign-off to proceed to remediation.

---

## Phase 1 – Remove PyMuPDF Dependencies

### 1.1 Update Dependencies
- Remove `PyMuPDF>=1.23.0` from `requirements.txt` and any other requirement files or lockfiles.
- Add Docling explicitly if not already locked (check `requirements.lock`, `artifacts/diagnostics/requirements.lock`, etc.). Include deterministic/offline configs as needed.
- Update documentation (`BLOCKERS_RESOLVED.md`, `TASKS_030_036_IMPLEMENTATION_GUIDE.md`, etc.) to note Docling as the required parser.

### 1.2 Adjust CI/Install Scripts
- Remove PyMuPDF install steps from automation scripts and CI workflows (`.github/workflows/*.yml`, PowerShell scripts, etc.).
- Ensure Docling is installed wherever ingestion tests run (add to setup or preflight scripts).

---

## Phase 2 – Replace PyMuPDF Parsing Logic

### 2.1 Ingestion Parser
- Replace `libs/ingestion/pdf_parser.py` with a Docling-based parser:
  - Use `DoclingBackend` (or its equivalent) to extract pages/tables.
  - Align output schema with existing ingestion pipeline (doc_id, page_num, text, metadata).
  - Remove all `fitz` imports and PyMuPDF-specific code paths.
- Update unit tests to cover Docling parsing.

### 2.2 Structure-Aware Chunker
- Refactor `libs/chunking/structure_aware_chunker.py` to consume Docling output:
  - Source text/metadata from Docling’s page-level results.
  - Remove PyMuPDF-based font/paragraph detection; reconstruct semantics using Docling metadata (headings, tables, etc.).
  - Ensure chunk metadata (char boundaries, section titles) remains consistent or is redefined for Docling output.
- Update CLI to operate on the new Docling-backed implementation.

### 2.3 Shared Parser Interfaces
- Update `libs/extraction/parser_backend.py` and `backend_default.py`:
  - Promote Docling backend to the default (and only) backend.
  - Remove PyMuPDF branch entirely; legacy helpers should raise or redirect to Docling.
- Adjust environment/config toggles (`PARSER_BACKEND`, `configs/pdf_backend.json`) to deprecate the “default/PyMuPDF” option, leaving Docling as canonical.

### 2.4 Scripts & Utilities
- Update scripts that currently import `fitz`:
  - `scripts/pdf_to_silver.py`, `scripts/create_test_bronze_data.py`, ingestion helpers.
  - Change parsing calls to Docling backend or to read the new Docling-generated parquet files.
  - Update CLI parameters to reflect Docling-only operation.

---

## Phase 3 – Tests & Fixtures

### 3.1 Test Suite Updates
- Update CP tests (`tests/cp/test_structure_aware_chunker.py`, `tests/cp/test_backend_docling.py`, ingestion tests) to run against Docling. Remove PyMuPDF-specific assertions/mocks.
- Regenerate test fixtures (e.g., chunk parquet files) from Docling output if necessary to match new semantics.
- Ensure coverage remains ≥95 % for chunker and backend modules after refactor.

### 3.2 Integration Tests & Validation Scripts
- Adjust integration tests or validation scripts (`scripts/finalize_031_035.ps1`, quality gates) that skip Docling tests to now require them.
- Update validation instructions in `EXECUTION_PLAN.md` if any gate names or dependencies change.

---

## Phase 4 – Documentation & Status Alignment

### 4.1 Update Reports
- Revise `artifacts/TASKS_031_036_FINAL_COMPLETION.md`, release notes, and implementation guides to reflect Docling-only ingestion.
- Remove references to PyMuPDF in README, onboarding guides, and validation reports.

### 4.2 Task Tracking
- If Docling adoption closes outstanding action items, update task manifests (`tasks/031-*`, `tasks/037-*`) and CP manifests accordingly.
- Any work remaining for Task 036 should still be marked deferred until resilience infrastructure is complete.

---

## Phase 5 – Follow-up Validation
1. Re-run the validation gates (at minimum V0–V6 from `EXECUTION_PLAN.md`) to confirm:
   - Chunker CLI succeeds without PyMuPDF.
   - Docling-based ingestion produces deterministic outputs.
   - Coverage remains ≥95 % for CP modules.
   - No residual doc/status inconsistencies (Task 036 still noted as deferred).
2. Update `STATUS.json` and `validation_report_037.json` with the new results.
3. Document any remaining work or risks in `remediation_notes.txt`.

---

### Hand-Off Checklist for Sonnet
- [ ] Install Docling in the working environment.
- [ ] Execute Phase 1 dependency removal and script updates.
- [ ] Refactor ingestion/chunking code per Phase 2.
- [ ] Update tests and fixtures as described in Phase 3.
- [ ] Refresh documentation and task status (Phase 4).
- [ ] Perform follow-up validation runs (Phase 5) and attach artefacts.

This plan, combined with the validation workflow in `EXECUTION_PLAN.md`, provides the full remediation roadmap to transition the ingestion pipeline to Docling exclusively.*** End Patch
