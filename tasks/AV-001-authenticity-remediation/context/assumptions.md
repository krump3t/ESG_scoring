# AV-001 Authenticity Remediation — Assumptions & Constraints

**Task**: Fix 203 authenticity violations (34 FATAL) across 6 phases
**Date**: 2025-10-26
**Protocol**: SCA v13.8-MEA

---

## Core Assumptions

### A1: Audit Report is Comprehensive and Accurate
**Assumption**: The output of `python scripts/qa/authenticity_audit.py` (run 2025-10-26) correctly identifies all 203 authenticity violations with no false negatives.

**Basis**:
- Audit tool is canonical per SCA v13.8
- Audit tool outputs structured JSON with file paths and line numbers
- AR-001 infrastructure (5 authenticity gates) is already implemented and working

**Risk**: If audit misses violations, post-remediation audit will re-detect them (fail Phase 6)

**Mitigation**: Re-run audit at end of Phase 6; if new violations appear, restart Phase 1-5 for that category

---

### A2: Baseline Git Snapshot is Recoverable
**Assumption**: `git tag audit-baseline-20251026` successfully locks pre-remediation state and can be used for emergency rollback via `git reset --hard`.

**Basis**:
- Git tag created immediately before remediation starts
- All uncommitted changes stashed before tag
- Tag points to specific commit hash (immutable)

**Risk**: If tag is accidentally deleted or reset, recovery is harder

**Mitigation**: Tag is annotated (not lightweight) with message; CI prevents tag deletion

---

### A3: All 523 Existing Tests Pass Pre-Remediation
**Assumption**: Full test suite (`pytest tests/ --cov`) passes 100% before remediation begins, providing a regression baseline.

**Basis**:
- AR-001 completion (7d6b3ce) includes passing full test suite
- No code changes between AR-001 and AV-001 start
- Test infrastructure (fixtures, mocks) is stable

**Risk**: If tests were flaky before remediation, we can't distinguish regressions from flakiness

**Mitigation**: Run test suite 3x before starting; only proceed if all 3 runs pass

---

### A4: Phase 1 (FATAL) Must Complete Before Phases 2-5
**Assumption**: All 34 eval/exec violations must be removed before proceeding to determinism/evidence/posture phases.

**Basis**:
- FATAL violations block scoring logic (code execution)
- Removing eval/exec may expose new non-determinism (Phase 2 will fix)
- Evidence parity (Phase 3) assumes code is already evaluated (not deferred)

**Risk**: If we attempt to seed randomness in Phase 2 before removing eval, we'll hit syntax errors

**Mitigation**: ADR-001.1 mandates sequential execution; Phase 1 must have 0 FATAL violations before Phase 2 starts

---

### A5: Determinism Can Be Achieved via FIXED_TIME + SEED
**Assumption**: Using environment variables `FIXED_TIME=1729000000.0` and `SEED=42` will make 3x runs byte-identical.

**Basis**:
- Clock abstraction (Task 019) already uses FIXED_TIME
- Numpy integration in libs/utils/determinism.py already uses SEED
- No randomness from external APIs (AR-001 enforces docker-only)

**Risk**: If some code paths use system time or hardware RNG bypassing our abstractions, 3x runs won't be identical

**Mitigation**: Phase 2 tests explicitly check for non-determinism; if detected, trace back to source

---

### A6: Evidence Parity Can Be Validated Without Production Database
**Assumption**: Using cached public ESG reports (Apple, Microsoft) is sufficient to validate parity enforcement; we don't need production company data.

**Basis**:
- All test data uses public ESG reports (investor relations)
- AR-001 parity tests already pass with cached data
- Production data is confidential/PII; would require additional redaction

**Risk**: If production data has different structure than public reports, parity validation might fail in prod

**Mitigation**: Phase 3 validation uses real SEC EDGAR URLs (cached); close enough to production format

---

### A7: Silent Failures Are Detectable via Test Execution
**Assumption**: Phase 5 (error handling) violations can be detected by running tests with various error conditions and verifying exceptions are not silenced.

**Basis**:
- Existing test suite includes failure-path tests
- New tests can be written to trigger specific error conditions
- Code review can identify silent exception handlers

**Risk**: If some error conditions are hard to trigger (race conditions, external API failures), they might remain hidden

**Mitigation**: Phase 5 includes both code review (grep for `except.*:`) and test coverage analysis

---

### A8: Docker-Only Constraint is Enforceably via Static Analysis
**Assumption**: Checking that code doesn't call external APIs (no `requests.get()`, no `socket.connect()`, etc.) is sufficient to verify docker-only compliance.

**Basis**:
- AR-001 Gate 5 (Docker-only) is already implemented
- /trace endpoint is read-only and no-network
- Static analysis (grep) can find most network calls

**Risk**: If code uses dynamic imports or reflection to call external APIs, static analysis will miss it

**Mitigation**: Phase 4 includes runtime network monitoring (e.g., via strace or tcpdump in Docker container)

---

## Constraints

### C1: Timeline Cannot Exceed 3 Days
**Constraint**: Remediation must complete by 2025-10-29 (3 days from start).

**Rationale**: Extended timeline risks feature freeze for dependent tasks (Task 018)

**Flexibility**: Day 3 afternoon buffer (3-6 hour contingency) built in; if Phase 5 overruns, Phase 6 can extend into Day 4

---

### C2: No New Dependencies Can Be Added
**Constraint**: Remediation must use existing libraries (no `pip install` new packages).

**Rationale**: Dependency changes require security audit; adds overhead

**Mitigation**: All remediation uses existing modules (os, json, hashlib, datetime, etc.)

---

### C3: No Database Schema Changes
**Constraint**: Remediation must not modify Iceberg schema, DuckDB tables, or data structures.

**Rationale**: Schema changes require data migration; out of scope for authenticity audit

**Mitigation**: Violations are code-only (eval/exec, randomness, error handling), not data

---

### C4: All Tests Must Pass at Phase Boundaries
**Constraint**: Before proceeding to next phase, full test suite must pass (0 regressions).

**Rationale**: Undetected regressions will compound across phases

**Mitigation**: Automated check: `pytest tests/ --cov` at end of each phase

---

### C5: Git History Must Remain Immutable
**Constraint**: No force-push, no rebase of public commits (only squash at PR review).

**Rationale**: Audit trail integrity (git history is regulatory artifact)

**Mitigation**: ADR-001.2 uses tags (immutable); commits are never amended

---

### C6: All Commits Must Reference Issue IDs
**Constraint**: Every commit message must include AV-001 issue ID (e.g., "Fix F001: eval in crawler.py").

**Rationale**: Traceability for regulatory audit

**Mitigation**: Commit template configured; pre-commit hook validates format

---

## External Dependencies

### D1: Git Repository Availability
**Dependency**: `git` CLI must be available and repository must be accessible.

**Status**: ✅ Confirmed (baseline tag created 2025-10-26)

---

### D2: Python 3.10+ with pytest, mypy, coverage
**Dependency**: Python runtime and test tools must be installed.

**Status**: ✅ Confirmed (AR-001 tests running)

---

### D3: Network Access (Baseline Only)
**Dependency**: During Phase 3 validation, need to fetch cached ESG reports (can be done offline if cached locally).

**Status**: ⚠️ Conditional (cached reports preferred, online fallback acceptable)

---

### D4: Write Access to Task Directory
**Dependency**: Must have write access to `tasks/AV-001-*/` directories.

**Status**: ✅ Confirmed (directory structure created)

---

## Risk Assumptions

### R1: Phase 1 Fixes Don't Break Functionality
**Assumption**: Removing eval/exec calls (Phase 1) won't break core scoring logic; alternative implementations exist.

**Mitigation**: Each eval/exec instance has an issue tracker entry with suggested replacement (e.g., "Use ast.literal_eval()")

---

### R2: Determinism Fixes Are Orthogonal to Other Phases
**Assumption**: Phase 2 fixes (seeding randomness) don't interfere with Phase 3-5 fixes (evidence, posture, errors).

**Basis**: FIXED_TIME and SEED are environment variables; don't affect code structure

---

### R3: 3x Identical Runs = Production Reproducibility
**Assumption**: If 3x runs produce byte-identical outputs, then production deployments will also be deterministic.

**Risk**: Production might have different runtime (different Python version, hardware, OS) causing non-determinism

**Mitigation**: Production deployment uses pinned requirements.txt and Docker image (identical runtime)

---

### R4: Real ESG Data Reflects Production Reality
**Assumption**: Using cached public reports (Apple, Microsoft) is a good proxy for confidential company ESG data.

**Risk**: Confidential data might have edge cases not in public reports

**Mitigation**: Phase 3 validation uses multiple real companies (Apple, Microsoft, LSE healthcare); covers diverse scenarios

---

## Sign-Off

**Assumptions reviewed**: All listed assumptions are explicit and validated
**Constraints understood**: All timeline/dependency/risk constraints documented
**Risk rating**: MEDIUM (Phase 1 complexity is highest risk; other phases lower)

**Ready to proceed**: ✅ YES

---

**Document**: AV-001 Assumptions & Constraints
**Version**: 1.0
**Created**: 2025-10-26
**Next Phase**: Create cp_paths.json and execution documents
