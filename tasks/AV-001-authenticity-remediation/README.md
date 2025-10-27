# AV-001: Authenticity Audit Remediation — Task Overview

**Task ID**: AV-001
**Title**: Authenticity Audit Remediation
**Protocol**: SCA v13.8-MEA
**Status**: 🔴 Ready for Execution
**Start Date**: 2025-10-27
**Target Date**: 2025-10-29 (3 days)
**Duration**: 14-22 hours

---

## What is AV-001?

**AV-001** is a systematic remediation task to fix 203 authenticity violations (34 FATAL, 87 Determinism, 29 Evidence, 12 Posture, 74 Errors) discovered in the ESG evaluation pipeline by the SCA authenticity audit (run 2025-10-26).

Unlike other tasks that **add features**, AV-001 **removes anti-patterns** (eval/exec), **enforces reproducibility** (determinism), and **ensures compliance** (evidence parity, error handling).

---

## The Problem

The ESG evaluation pipeline contains:
- 34 eval/exec calls (security risk, blocks analysis)
- 87 unseeded randomness operations (destroys reproducibility)
- 29 evidence parity violations (compliance gap)
- 12 production posture issues (type safety, error handling)
- 74 silent failure patterns (robustness gap)

**Impact**: Non-deterministic, non-auditable, non-compliant scoring system.

**Solution**: Systematic 6-phase remediation across 3 days.

---

## The Solution: 6-Phase Remediation

```
Phase 1 (FATAL):      Remove 34 eval/exec calls
Phase 2 (Determinism): Seed 87 randomness operations
Phase 3 (Evidence):    Enforce 29 parity/rubric rules
Phase 4 (Posture):     Fix 12 production issues
Phase 5 (Errors):      Handle 74 silent failures
Phase 6 (Verify):      Confirm 0 violations remain
```

**Success Criteria**:
- ✅ 0 violations remaining (audit = 0)
- ✅ 523 tests passing
- ✅ Type safety: mypy --strict = 0 errors
- ✅ Determinism: 3x identical runs
- ✅ Coverage: ≥95%
- ✅ Docker offline: working

---

## Documents in This Task

### 1. **EXECUTIVE_SUMMARY.md** (Entry Point)
**Read this FIRST** (5 minutes)
- High-level violation breakdown
- Visual roadmap
- Quick start checklist
- Critical path
- Success criteria

### 2. **QUICK_START_CHECKLIST.md** (Daily Guide)
**Use this DAILY** during work
- Day 1/2/3 phase-by-phase tasks
- Checkboxes to mark progress
- Quick reference commands
- End-of-day verification

### 3. **REMEDIATION_PLAN.md** (Detailed Reference)
**Consult when you need code examples**
- Phase 0-6 detailed guides
- Code examples (before/after)
- Test commands
- Verification procedures
- Quick reference commands

### 4. **ISSUE_TRACKER.md** (Progress Tracking)
**Update DAILY**
- All 203 issues organized by priority
- Status checkboxes per issue
- Acceptance criteria
- Daily velocity tracking
- Final sign-off checklist

### 5. **TROUBLESHOOTING_GUIDE.md** (When Stuck)
**Use when encountering errors**
- Symptom-based diagnosis trees
- Common causes and fixes
- Emergency procedures
- Getting help checklist

### 6. **Context Files** (Task Scaffolding)
Located in `context/` directory:
- `hypothesis.md` - Metrics and success criteria
- `design.md` - Verification strategy
- `evidence.json` - Data sources
- `data_sources.json` - Source details
- `adr.md` - Architectural decisions
- `assumptions.md` - Assumptions & constraints
- `cp_paths.json` - Critical path file patterns

---

## How to Use This Task

### First Time (30 minutes)
1. **Read EXECUTIVE_SUMMARY.md** (5 min) — Understand scope
2. **Read this README** (5 min) — You're doing it now ✅
3. **Review QUICK_START_CHECKLIST.md Day 1 morning** (5 min) — See today's tasks
4. **Run setup commands** from REMEDIATION_PLAN.md Phase 0 (10 min)
5. **Begin Phase 1** — Start first FATAL violation fix

### During Work (Daily)
1. **Open QUICK_START_CHECKLIST.md** — See today's tasks
2. **Complete Phase tasks** — Use REMEDIATION_PLAN.md for code examples
3. **Update ISSUE_TRACKER.md** — Mark issues as you fix them
4. **Run verification commands** — After each phase completion
5. **Commit work** — With issue IDs in message
6. **If stuck** — Check TROUBLESHOOTING_GUIDE.md

### End of Day
1. **Update ISSUE_TRACKER.md** — Mark phase as complete
2. **Run full test suite** — `pytest tests/ --cov`
3. **Tag phase checkpoint** — `git tag audit-phaseN-complete-<hash>`
4. **Commit summary** — `git commit -m "docs(AV-001): End of Day X — Phase N complete"`

### End of Day 3
1. **Run final audit** — `python scripts/qa/authenticity_audit.py`
2. **Verify 0 violations** — All checks pass
3. **Tag final** — `git tag v1.0.0-audit-clean`
4. **Generate completion report** — Document results

---

## Key Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| Total Violations | 0 | `python scripts/qa/authenticity_audit.py \| jq length` |
| FATAL Violations | 0 | `grep -r "eval\|exec" scripts/ agents/ apps/ libs/` |
| Test Pass Rate | 523/523 | `pytest tests/ --cov` |
| Type Safety | 0 errors | `mypy --strict apps/ agents/ libs/` |
| Coverage | ≥95% | `pytest --cov-report=term` |
| Determinism | 3x identical | `bash /tmp/test_det.sh` |
| Docker Offline | Working | `docker run --network none esg-scorer /trace` |

---

## Critical Success Factors

### MUST DO's:
✅ Follow phases in exact order (1 → 2 → 3 → 4 → 5 → 6)
✅ Complete Phase 1 (FATAL) before anything else
✅ Test after every sub-phase (run full suite)
✅ Commit frequently with clear messages (include issue ID)
✅ Update ISSUE_TRACKER.md daily
✅ Verify all gates pass before declaring complete

### NEVER DO's:
❌ Skip Phase 1 (it blocks everything)
❌ Work on multiple phases in parallel
❌ Commit without testing
❌ Push to main before all gates pass
❌ Leave uncommitted work at end of day

---

## Timeline

### Day 1 (7-12 hours): Phases 1-2
- **Phase 1 (4-7h)**: Remove 34 eval/exec calls
- **Phase 2 (3-5h)**: Seed 87 randomness operations
- **Checkpoint**: 0 FATAL violations, determinism verified

### Day 2 (7-10 hours): Phases 3-4
- **Phase 3 (4-6h)**: Enforce 29 parity/rubric rules
- **Phase 4 (3-4h)**: Fix 12 production issues
- **Checkpoint**: Evidence validated, type safety confirmed

### Day 3 (3-6 hours): Phases 5-6
- **Phase 5 (2-3h)**: Handle 74 silent failures
- **Phase 6 (2-3h)**: Final verification & sign-off
- **Checkpoint**: 0 violations, all tests pass, tagged

---

## Environment Setup

```bash
# Set environment variables (once at start)
export FIXED_TIME=1729000000.0
export SEED=42
export PYTHONHASHSEED=0

# Verify Python
python --version  # Expected: Python 3.10+
pytest --version  # Expected: pytest 7.0+
mypy --version    # Expected: mypy 1.0+

# Verify git
git status  # Expected: On branch master
git log -1 --oneline  # Shows current state
```

---

## Command Quick Reference

```bash
# Phase 0: Setup
git tag -a audit-baseline-20251026 -m "Pre-remediation"
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json

# Phase 1: Check eval/exec
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l

# Phase 2: Determinism test
export FIXED_TIME=1729000000.0 SEED=42
bash /tmp/test_det.sh

# Phase 3: Parity check
python scripts/qa/verify_parity.py

# Phase 4: Type safety
mypy --strict apps/ agents/ libs/ scripts/

# All phases: Full test
pytest tests/ --cov

# Final: Audit
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json

# Verification
grep -c '"violation_id"' artifacts/audit_final.json  # Should be 0
```

---

## Success Looks Like

**End of Day 3:**
```
✅ 34 FATAL violations fixed
✅ 87 Determinism violations fixed
✅ 29 Evidence violations fixed
✅ 12 Posture violations fixed
✅ 74 Error violations fixed
────────────────────────
✅ 203/203 violations resolved (100%)

✅ Audit: 0 violations
✅ Tests: 523/523 pass, ≥95% coverage
✅ Type Safety: mypy --strict = 0 errors
✅ Determinism: 3x identical runs
✅ Docker: Offline test passes
✅ Final commit: v1.0.0-audit-clean

Status: 🚀 PRODUCTION READY
```

---

## Roles During Remediation

### Code Author
- Write fixes
- Test thoroughly
- Commit with issue IDs

### Auditor
- Verify each phase
- Run verification commands
- Update ISSUE_TRACKER

### Compliance Officer
- Ensure git history immutable
- Document decisions
- Sign off final results

---

## Documentation Map

```
AV-001-authenticity-remediation/
├── README.md (this file) ← Start here
├── EXECUTIVE_SUMMARY.md ← Read next
├── QUICK_START_CHECKLIST.md ← Daily guide
├── REMEDIATION_PLAN.md ← Code examples
├── ISSUE_TRACKER.md ← Progress tracking
├── TROUBLESHOOTING_GUIDE.md ← Problem solving
├── context/
│   ├── hypothesis.md
│   ├── design.md
│   ├── evidence.json
│   ├── data_sources.json
│   ├── adr.md
│   ├── assumptions.md
│   └── cp_paths.json
├── artifacts/ (generated during work)
├── qa/ (logs generated during work)
└── reports/ (phase summaries generated during work)
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Phase 1 fixes break code | CRITICAL | Each fix has test; full suite after each |
| Determinism not achievable | HIGH | Clock/SEED infrastructure proven in AR-001 |
| Parity too strict | MEDIUM | Test with real data; relax if needed |
| Time estimate wrong | MEDIUM | Day 3 buffer built in (3-6h) |
| Missed violations | LOW | Re-run audit at end (will catch) |

---

## Getting Help

**Before asking for help**:
1. [ ] Check TROUBLESHOOTING_GUIDE.md (symptom lookup)
2. [ ] Follow diagnosis tree
3. [ ] Try suggested fix
4. [ ] Verify with test command
5. [ ] Still stuck after 30 minutes?

**When asking, provide**:
- Phase number
- Error message (full text)
- What you tried
- File and line number (if applicable)
- `git log -1 --oneline` (show current commit)

---

## Sign-Off & Approval

**Task Status**: 🔴 Ready for Execution
**Baseline Created**: 2025-10-26
**Timeline**: 3 days (2025-10-27 → 2025-10-29)
**Contingency**: Rollback to git tag `audit-baseline-20251026`

---

## Next Steps

1. **NOW**: Read EXECUTIVE_SUMMARY.md (5 minutes)
2. **NEXT**: Review QUICK_START_CHECKLIST.md Day 1 morning (5 minutes)
3. **THEN**: Run Phase 0 setup commands from REMEDIATION_PLAN.md (10 minutes)
4. **START**: Phase 1 — Remove first eval/exec instance (10 minutes in)

---

## Document Info

**Title**: AV-001 Task Overview & Navigation Guide
**Version**: 1.0
**Created**: 2025-10-26
**Protocol**: SCA v13.8-MEA
**Status**: Ready for execution

---

**Your journey to production-ready authenticity starts with EXECUTIVE_SUMMARY.md. Read it now!** 📖🚀
