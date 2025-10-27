# Task 019: Authenticity Infrastructure — Context Files Summary

**Created**: 2025-10-26
**Status**: Ready for Manual Review
**Protocol**: SCA v13.8-MEA

---

## Overview

All required context files for Task 019-authenticity-infrastructure have been created and are ready for your manual review. This task will remediate all 149 authenticity violations identified in the comprehensive audit.

---

## Files Created

### Directory Structure
```
tasks/019-authenticity-infrastructure/
├── context/                      ✅ COMPLETE
│   ├── hypothesis.md             ✅ 240 lines (9,774 bytes)
│   ├── design.md                 ✅ 614 lines (21,229 bytes)
│   ├── evidence.json             ✅ 91 lines (6,337 bytes)
│   ├── data_sources.json         ✅ 81 lines (3,355 bytes)
│   ├── cp_paths.json             ✅ 6 lines (134 bytes)
│   ├── adr.md                    ✅ 231 lines (8,342 bytes)
│   └── assumptions.md            ✅ 271 lines (9,743 bytes)
├── artifacts/                    ✅ (empty, ready for Phase 1)
├── qa/                           ✅ (empty, ready for test runs)
└── reports/                      ✅ (empty, ready for snapshots)

**Total Context Lines**: 1,534 lines (~59 KB)
```

---

## File Summaries

### 1. hypothesis.md (240 lines)
**Purpose**: Define success criteria, metrics, and critical path modules

**Key Sections**:
- **Primary Claim**: Remediate 149 violations → <5 with full determinism infrastructure
- **Success Criteria (SC19.1-SC19.6)**:
  - SC19.1: Audit status = "ok" (0 FATAL)
  - SC19.2: Deterministic behavior (10 runs with SEED=42 produce identical SHA256)
  - SC19.3: Clock abstraction coverage (100% of 81 violations)
  - SC19.4: HTTP abstraction coverage (100% of 33 violations)
  - SC19.5: Exception handling (0 silent handlers in CP code)
  - SC19.6: Coverage ≥95% on infrastructure modules
- **Critical Path Modules**: clock.py, determinism.py, http_client.py, exemptions.json
- **Metrics**: 149 violations → <5, determinism hash stability, network isolation
- **Verification Strategy**: 5 validation methods (determinism test, differential test, network isolation, coverage, audit re-run)

### 2. design.md (614 lines)
**Purpose**: Detailed implementation plan with 6 phases

**Key Sections**:
- **Audit Integration**: Reference to artifacts/authenticity/report.json (149 violations)
- **Data Strategy**: Input data, phase-by-phase rollout, leakage guards
- **Architecture**: Three-layer design (Application → Infrastructure → Configuration)
- **6-Phase Implementation**:
  - Phase 1: FATAL fix (unseeded random) - 2 hours
  - Phase 2: Clock abstraction (81 violations) - 16 hours
  - Phase 3: HTTP abstraction (33 violations) - 12 hours
  - Phase 4: Exception handling (10 violations) - 4 hours
  - Phase 5: Parquet migration (16 violations) - 6 hours
  - Phase 6: Task 018 coverage fix - 3 hours
- **Testing Strategy**: Unit tests (TDD guard compliance), integration tests, differential testing
- **Acceptance Criteria**: 7 gates for task completion

### 3. evidence.json (91 lines)
**Purpose**: Document primary sources for design decisions

**Key Sections**:
- **3 P1 Sources** (required by SCA v13.8):
  1. Stodden et al. (Science 2016) - Reproducible Research in Computational Science
  2. Groce et al. (ICSE 2014) - Effective Testing Strategies for Deterministic Software
  3. Fowler (PoEAA) - Dependency Injection Patterns
- **Secondary Sources**: pytest fixtures, Hypothesis property testing, requests-mock
- **Data Sources Referenced**: Audit report, remediation plan
- **Validation Status**: Complete with retrieval dates and ≤50-word syntheses

### 4. data_sources.json (81 lines)
**Purpose**: Document all data inputs with provenance

**Key Sections**:
- **Source 1**: authenticity_audit_report
  - Path: artifacts/authenticity/report.json
  - SHA256: 51b973cb28e17e786d97299817a6978ea596893fb1bc886fe94e4619b6eae96d (computed)
  - Size: 58,112 bytes
  - PII flag: false
  - Contains: 149 violations (9 FATAL, 140 WARN)
- **Source 2**: authenticity_remediation_plan
  - Path: AUTHENTICITY_REMEDIATION_PLAN.md
  - 6 phases, 43 hours effort, 3-week timeline
- **Source 3**: existing_codebase_violations
  - 149 files affected across agents/, apps/, libs/, scripts/, tests/
- **Data Integrity**: Leakage guards, no normalization (code remediation task)

### 5. cp_paths.json (6 lines)
**Purpose**: Define critical path modules for validation

**CP Modules**:
1. `**/libs/utils/clock.py`
2. `**/libs/utils/determinism.py`
3. `**/libs/utils/http_client.py`
4. `**/.sca/exemptions.json`

### 6. adr.md (231 lines)
**Purpose**: Document architectural decisions

**5 ADRs**:
- **ADR-019-001**: Dependency Injection vs Monkey-Patching (ACCEPTED: Dependency Injection)
- **ADR-019-002**: JSON Exemption Registry Format (ACCEPTED: .sca/exemptions.json)
- **ADR-019-003**: Gradual Rollout Strategy (ACCEPTED: Top 20 high-impact files first)
- **ADR-019-004**: HTTPClient Interface Design (ACCEPTED: Minimal interface - get/post only)
- **ADR-019-005**: Test Fixture Generation (ACCEPTED: Captured fixtures from live APIs)

### 7. assumptions.md (271 lines)
**Purpose**: Document technical assumptions and constraints

**10 Technical Assumptions**:
1. Existing tests do not rely on wall-clock time
2. Production deployments can set FIXED_TIME env var
3. HTTP fixtures can be generated from live API responses
4. Existing code can tolerate Clock/HTTP injection
5. SEED env var universally respected
6. Test suite tolerates zero network access
7. Exemption registry covers all intentional violations
8. 3-week sprint timeline is achievable
9. Task 018 coverage gap is isolated to 2-3 missing branches
10. No PII in violation data or audit reports

**Dependency Assumptions**:
- Upstream: Authenticity audit (AV-001) ✅ COMPLETE
- Downstream: Task 020+ blocked until Task 019 complete

**3 Constraints**:
1. No breaking changes to public APIs
2. No external dependencies for infrastructure modules
3. Zero tolerance for placeholders in CP modules

---

## Compliance with SCA v13.8 Context Gate

✅ **hypothesis.md**: Metrics, thresholds, CP files, exclusions, power analysis
✅ **design.md**: Data strategy, verification plan, success thresholds, leakage guards
✅ **evidence.json**: ≥3 P1 sources with DOI/URLs, ≤50-word syntheses, retrieval dates
✅ **data_sources.json**: Sources with SHA256, PII flag, provenance, retention
✅ **cp_paths.json**: Glob patterns for CP files (4 modules)
✅ **adr.md**: Architectural decisions (5 ADRs, all non-empty)
✅ **assumptions.md**: Dependencies, constraints, risks (non-empty)

**Status**: All required context files present and complete

---

## Next Steps (After Your Manual Review)

1. **Review Context Files**:
   - Read through each file to ensure accuracy and completeness
   - Verify metrics and success criteria align with project goals
   - Check ADRs for soundness of architectural decisions
   - Validate assumptions against project constraints

2. **Approve or Request Changes**:
   - If approved: Proceed to context gate validation
   - If changes needed: Provide feedback for revision

3. **Execute Context Gate Validation** (after approval):
   ```bash
   bash "C:\projects\Work Projects\sca-protocol-skill\commands\validate-only.sh"
   ```
   - Expected result: `context_gate: true` (all files present and valid)

4. **Begin Phase 1 Implementation** (after context gate passes):
   - TDD approach: Write tests FIRST for libs/utils/determinism.py
   - Implement determinism.py
   - Fix unseeded random in apps/mcp_server/server.py:46
   - Run validation → status: "ok" for Phase 1

5. **Iterative MEA Loop** for Phases 2-6:
   - Write → Validate → Fix → Repeat until all gates pass

---

## Questions for Review

Please consider the following during your review:

1. **Scope**: Are 6 phases appropriate, or should we split/merge any?
2. **Timeline**: Is 3 weeks realistic, or do we need buffer time?
3. **Metrics**: Are SC19.1-SC19.6 measurable and achievable?
4. **ADRs**: Do the architectural decisions align with team standards?
5. **Assumptions**: Are there additional constraints we should document?
6. **CP Modules**: Should any other files be marked as Critical Path?

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Context Files Created | 7 |
| Total Lines | 1,534 |
| Total Size | ~59 KB |
| P1 Evidence Sources | 3 (required: ≥3) ✅ |
| ADRs Documented | 5 |
| Assumptions Documented | 10 |
| CP Modules | 4 |
| Phases Planned | 6 |
| Total Effort Estimate | 43 hours |
| Timeline | 3 weeks (Sprint 3) |
| Target Violations | 149 → <5 |

---

**Status**: ✅ All context files created and ready for manual review

**Next Action**: Awaiting your review and approval to proceed with context gate validation
