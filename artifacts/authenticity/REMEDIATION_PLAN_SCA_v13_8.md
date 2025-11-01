## SCA v13.8 Remediation Plan

This file outlines a step-by-step remediation plan to reach full SCA v13.8 compliance. It includes phases, verification steps, artifacts, acceptance criteria, approval checkpoints, estimated effort, and rollback guidance.

Generated: 2025-10-27
Protocol Reference: `full_protocol.md` (v13.8)

---

### Phase 1 — Protocol Alignment

- Changes: update `.sca_config.json` to v13.8; add `.claude/CLAUDE.md` linking canonical protocol.
- Verification: config fields match Full Protocol §8; primer path verified.
- Artifacts: `artifacts/compliance_status.md` with protocol + thresholds.
- Acceptance: matches §8 and §11 exactly.
- Approval: confirm config + primer.
- Effort: ~0.5h. Rollback: restore old config.

### Phase 2 — Validators + Review Gate

- Changes: add `validators/placeholders_cp.py`; extend runner with gates + `validate review`; generate compliance_status.
- Verification: placeholder injected → fails; removed → passes.
- Artifacts: `artifacts/compliance_status.md`.
- Acceptance: review gate reliably detects placeholders.
- Approval: runner and artifact format.
- Effort: ~2–3h. Rollback: revert validator/runner.

### Phase 3 — Dependency Hygiene

- Changes: pin `requirements*.txt`; add `requests==<pin>`.
- Verification: `scripts/check_dependencies.py` PASS.
- Artifacts: `artifacts/deps/dependency_check.txt`.
- Acceptance: no wildcard/unpinned (except allowed).
- Approval: approve pins.
- Effort: ~1–2h. Rollback: restore requirements.

### Phase 4 — CP Authenticity Fixes (Stubs, Time)

- Changes: remove const-return stub in `apps/scoring/scorer.py` or guard with `# @allow-const` + tests; replace wall-clock with `get_clock()`; remove placeholder scores.
- Verification: `@pytest.mark.cp` varied-input + failure-path tests.
- Artifacts: updated tests/docs.
- Acceptance: `authenticity_ast` + `placeholders_cp` pass.
- Approval: review diffs + tests.
- Effort: ~2–3h. Rollback: revert modules.

### Phase 5 — Network Boundary in CP

- Changes: remove direct `requests` from CP; inject `HTTPClient`; tests use `MockHTTPClient`.
- Verification: grep shows no `import requests` under CP paths.
- Artifacts: tests demonstrating mocks.
- Acceptance: zero direct network imports in CP.
- Approval: DI interfaces.
- Effort: ~1–2h. Rollback: revert DI.

### Phase 6 — JSON-as-Parquet Remediation

- Changes: replace artifact `to_json()` with `to_parquet()` in production paths; transitional dual-write if needed.
- Verification: schema/read-write parity tests.
- Artifacts: `artifacts/migrations/json_to_parquet.md`.
- Acceptance: authenticity audit clears json_as_parquet in prod.
- Approval: affected interfaces.
- Effort: ~1–2h. Rollback: re-enable JSON.

### Phase 7 — Exception Handling Hardening

- Changes: replace silent `except` with logging + raise/defined errors.
- Verification: failure-path tests capture exceptions.
- Artifacts: `artifacts/qa/exception_hardening_report.md`.
- Acceptance: audit clears silent_exception in prod.
- Approval: error-handling policy.
- Effort: ~1–2h. Rollback: revert blocks.

### Phase 8 — Determinism Proof

- Changes: complete audit determinism test; run pipeline twice with FIXED_TIME and PYTHONHASHSEED=0.
- Verification: identical `diff_hashes.json` across runs.
- Artifacts: `artifacts/authenticity/diff_hashes.json`, updated `report.*`.
- Acceptance: determinism PASS.
- Approval: determinism scope.
- Effort: ~1–2h. Rollback: prior audit kept.

### Phase 9 — Compliance Artifacts Consistency

- Changes: reconcile `tasks/COMPLIANCE_REPORT.json` vs `tasks/validation_report.json`; generate `compliance_status.md` each validate.
- Verification: aligned pass/fail, timestamps, evidence links.
- Artifacts: updated compliance files.
- Acceptance: no contradictions.
- Approval: reporting format.
- Effort: ~0.5–1h. Rollback: restore originals.

### Phase 10 — CI and MR Enforcement

- Changes: CI job for `validate review`; MR template with 3 checkboxes.
- Verification: CI blocks noncompliant MRs.
- Artifacts: CI config, MR template.
- Acceptance: reliable enforcement.
- Approval: CI/MR changes.
- Effort: ~1h. Rollback: disable job/template.

### Phase 11 — Final Audit and Sign-off

- Changes: run authenticity audit and full validate.
- Verification: 0 fatal; warnings triaged/exempted; all required gates pass.
- Artifacts: final `ANALYSIS_REPORT.md`, `REMEDIATION_LOG.md`, snapshots.
- Acceptance: SCA v13.8 satisfied; sign-off recorded.
- Approval: final merge/tag.
- Effort: ~0.5h. Rollback: N/A.

