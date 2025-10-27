# AV-001 Execution Roadmap — Next Steps & Phase Sequence

**Current State**: Scaffolding complete, ready for Phase 0 execution
**Date**: 2025-10-26
**Target Start**: 2025-10-27 (Day 1)
**Target End**: 2025-10-29 (Day 3)

---

## Current Completion State

### ✅ Completed (Scaffolding Phase)
- [x] Task directory structure created (artifacts/, qa/, reports/, context/)
- [x] All 7 context files created (SCA compliance)
- [x] All 6 execution documents created
- [x] .sca/profile.json updated (current_task = AV-001)
- [x] Verification alignment confirmed
- [x] 13 total deliverable files ready

### ⏳ Pending (Execution Phases)
- [ ] Phase 0: Pre-remediation setup (5 minutes)
- [ ] Phase 1: Remove eval/exec (4-7 hours)
- [ ] Phase 2: Determinism (3-5 hours)
- [ ] Phase 3: Evidence parity (4-6 hours)
- [ ] Phase 4: Production posture (3-4 hours)
- [ ] Phase 5: Error handling (2-3 hours)
- [ ] Phase 6: Final verification (2-3 hours)

---

## Next Phase: Phase 0 — Pre-Remediation Setup (5 minutes)

### **When**: Right before beginning Phase 1
### **Duration**: 5 minutes
### **Prerequisite**: All scaffolding complete (✅ done)

### **Phase 0 Steps**

#### Step 0.1: Create Baseline Git Tag (2 minutes)
```bash
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
git status  # Verify clean working directory
git tag -a audit-baseline-20251026 -m "AV-001 pre-remediation baseline snapshot"
git log -1 --oneline  # Verify tag applied
```

**Purpose**: Creates immutable snapshot for emergency rollback
**Success Criterion**: Tag appears in `git tag -l`

---

#### Step 0.2: Capture Baseline Audit (2 minutes)
```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json

# Verify output
python -c "
import json
data = json.load(open('artifacts/audit_baseline.json'))
print(f'Total violations: {len(data)}')
by_severity = {}
for v in data:
    sev = v.get('severity', 'unknown')
    by_severity[sev] = by_severity.get(sev, 0) + 1
print('By severity:', by_severity)
"
```

**Expected Output**:
```
Total violations: 203
By severity: {0: 34, 1: 87, 2: 29, 3: 12, 4: 74}
```

**Purpose**: Establishes baseline for comparison after each phase
**Success Criterion**: Output shows exactly 203 violations with correct distribution

---

#### Step 0.3: Verify Test Suite Baseline (1 minute)
```bash
pytest tests/ --cov -q
# Expected: 523 passed in X.XXs
```

**Purpose**: Ensures no regressions already present
**Success Criterion**: `523 passed` (no failures, no errors)

---

### **Phase 0 Completion Checklist**
- [ ] Baseline git tag created: `audit-baseline-20251026`
- [ ] Baseline audit captured: `artifacts/audit_baseline.json`
- [ ] Baseline audit shows: 203 violations (34/87/29/12/74 split)
- [ ] All tests passing: 523/523
- [ ] Git working directory clean
- [ ] Ready to begin Phase 1 ✅

---

## Execution Sequence: Phases 1-6

### **Phase 1: Remove eval() and exec() — FATAL Violations (4-7 hours)**

**Objective**: Eliminate 34 FATAL violations blocking all other work

**Sub-tasks** (from QUICK_START_CHECKLIST.md Day 1 Morning):
1. Identify all eval() instances (15 min)
2. Identify all exec() instances (15 min)
3. Fix eval/exec batch 1 (60-90 min)
4. Check progress (5 min)
5. Fix eval/exec batch 2 (60-90 min)
6. Final eval/exec check (30 min)
7. Audit Phase 1 completion (10 min)

**Verification Commands**:
```bash
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l
# Expected: 0

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase1.json
pytest tests/ --cov -q
# Expected: 523 passed, FATAL violations = 0
```

**Success Criterion**: Zero eval/exec found, audit shows 0 FATAL violations, all tests pass

**Next Trigger**: When Phase 1 audit shows 0 FATAL violations → Proceed to Phase 2

---

### **Phase 2: Determinism — Seed All Randomness (3-5 hours)**

**Objective**: Enable reproducible computation (3x identical runs)

**Sub-tasks** (from QUICK_START_CHECKLIST.md Day 1 Afternoon):
1. Identify unseeded randomness (15 min)
2. Identify non-deterministic time ops (15 min)
3. Add SEED initialization to modules (60 min)
4. Fix time-based operations (60 min)
5. Determinism validation (30-60 min)
6. Phase 2 completion audit (10 min)

**Verification Commands**:
```bash
export FIXED_TIME=1729000000.0 SEED=42 PYTHONHASHSEED=0
bash /tmp/test_det.sh
# Expected: ✅ DETERMINISM VERIFIED: All 3 runs identical

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase2.json
pytest tests/ --cov -q
# Expected: 523 passed, Determinism violations near 0
```

**Success Criterion**: 3x determinism test passes, all tests still pass

**Next Trigger**: When determinism test shows byte-identical outputs → Proceed to Phase 3

---

### **Phase 3: Evidence Parity & Rubric Compliance (4-6 hours)**

**Objective**: Enforce evidence-first scoring (≥2 quotes, parity validation)

**Sub-tasks** (from QUICK_START_CHECKLIST.md Day 2 Morning):
1. Enforce rubric MIN_QUOTES = 2 (90 min)
2. Implement parity validation (90 min)
3. Validate evidence contract (60 min)
4. Phase 3 completion audit (10 min)

**Verification Commands**:
```bash
python scripts/qa/verify_parity.py
# Expected: PASS

pytest tests/retrieval/ -k parity -v
pytest tests/scoring/ -k rubric -v
# Expected: All pass

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase3.json
pytest tests/ --cov -q
# Expected: 523 passed, Evidence violations ≈ 0
```

**Success Criterion**: Parity check passes, rubric enforcement active, all tests pass

**Next Trigger**: When evidence violations resolved → Proceed to Phase 4

---

### **Phase 4: Production Posture — Type Safety & Error Handling (3-4 hours)**

**Objective**: Production-ready code quality

**Sub-tasks** (from QUICK_START_CHECKLIST.md Day 2 Afternoon):
1. Fix type safety issues (mypy --strict) (60 min)
2. Add error handling to APIs (60 min)
3. Verify Docker offline compliance (30 min)
4. Phase 4 completion audit (10 min)

**Verification Commands**:
```bash
mypy --strict apps/ agents/ libs/ scripts/
# Expected: 0 errors

docker run --network none esg-scorer /trace
# Expected: 200 OK

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase4.json
pytest tests/ --cov -q
# Expected: 523 passed, Posture violations = 0
```

**Success Criterion**: Type safety = 0 errors, Docker offline works, all tests pass

**Next Trigger**: When type checks and Docker test pass → Proceed to Phase 5

---

### **Phase 5: Silent Failure Detection — Logging & Error Handling (2-3 hours)**

**Objective**: Comprehensive error handling and logging

**Sub-tasks** (from QUICK_START_CHECKLIST.md Day 3 Morning):
1. Detect and log silent failures (60 min)
2. Add exception handling throughout (60 min)
3. Phase 5 completion audit (10 min)

**Verification Commands**:
```bash
pytest tests/ -k error -v
# Expected: All pass

pytest tests/ --cov=agents,apps,libs --cov-report=term | grep TOTAL
# Expected: ≥95%

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase5.json
```

**Success Criterion**: Error tests pass, coverage ≥95%, error violations resolved

**Next Trigger**: When error handling comprehensive → Proceed to Phase 6

---

### **Phase 6: Final Verification — All Gates Passing (2-3 hours)**

**Objective**: Zero violations, production-ready system

**Sub-tasks** (from QUICK_START_CHECKLIST.md Day 3 Afternoon):
1. Run final complete audit (5 min)
2. Run full test suite with coverage (30 min)
3. Final type safety check (5 min)
4. Final determinism verification (10 min)
5. Final Docker offline test (5 min)
6. Create completion report (30 min)
7. Tag and commit (5 min)

**Verification Commands**:
```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json
# Expected: 0 violations

pytest tests/ --cov=agents,apps,libs --cov-report=html,term
# Expected: 523/523 pass, ≥95% coverage

mypy --strict apps/ agents/ libs/ scripts/
# Expected: 0 errors

bash /tmp/test_det.sh
# Expected: ✅ DETERMINISM VERIFIED

docker run --network none esg-scorer /trace
# Expected: 200 OK
```

**Success Criterion**: All gates pass, 0 violations remaining

**Completion Actions**:
```bash
# Create completion report
# Tag final commit
git tag -a v1.0.0-audit-clean -m "AV-001 Complete — All 203 violations resolved"

# Push to repository
git push origin v1.0.0-audit-clean
```

---

## Phase Progression Flow Chart

```
Phase 0 (Setup)
    ↓ [5 min]
    Baseline tag created ✓
    Baseline audit captured ✓
    Tests verified ✓
    ↓
Phase 1 (FATAL)
    ↓ [4-7 hours]
    Remove 34 eval/exec ✓
    0 FATAL violations ✓
    523 tests passing ✓
    ↓
Phase 2 (Determinism)
    ↓ [3-5 hours]
    Seed 87 randomness ops ✓
    3x identical runs ✓
    523 tests passing ✓
    ↓
Phase 3 (Evidence)
    ↓ [4-6 hours]
    Enforce 29 parity/rubric ✓
    Parity validation active ✓
    523 tests passing ✓
    ↓
Phase 4 (Posture)
    ↓ [3-4 hours]
    Fix 12 production issues ✓
    Type safety = 0 errors ✓
    Docker offline works ✓
    ↓
Phase 5 (Errors)
    ↓ [2-3 hours]
    Handle 74 silent failures ✓
    Coverage ≥95% ✓
    523 tests passing ✓
    ↓
Phase 6 (Verify)
    ↓ [2-3 hours]
    Final audit = 0 violations ✓
    All gates passing ✓
    Final tag: v1.0.0-audit-clean ✓
    ↓
🚀 PRODUCTION READY
```

---

## Daily Timeline

### **Day 1 (2025-10-27): 7-12 hours**
- **Morning (4-7h)**: Phase 1 — Remove eval/exec (34 issues)
- **Afternoon (3-5h)**: Phase 2 — Determinism (87 issues)
- **End of Day**: Phase 1-2 complete, 121/203 violations fixed
- **Checkpoints**:
  - 0 FATAL violations remaining
  - 3x determinism test passes
  - 523 tests passing
  - Tag: `audit-phase2-complete-<hash>`

### **Day 2 (2025-10-28): 7-10 hours**
- **Morning (4-6h)**: Phase 3 — Evidence parity (29 issues)
- **Afternoon (3-4h)**: Phase 4 — Production posture (12 issues)
- **End of Day**: Phase 3-4 complete, 162/203 violations fixed
- **Checkpoints**:
  - Evidence parity validated
  - Type safety = 0 errors
  - Docker offline works
  - 523 tests passing
  - Tag: `audit-phase4-complete-<hash>`

### **Day 3 (2025-10-29): 3-6 hours**
- **Morning (2-3h)**: Phase 5 — Error handling (74 issues)
- **Afternoon (2-3h)**: Phase 6 — Final verification
- **End of Day**: All 203/203 violations fixed, PRODUCTION READY
- **Checkpoints**:
  - 0 violations remaining
  - All gates passing
  - 523 tests passing
  - Coverage ≥95%
  - Tag: `v1.0.0-audit-clean`

---

## Success Metrics by Phase

### Phase 0: Setup
- [ ] Baseline tag exists
- [ ] Baseline audit = 203 violations
- [ ] All tests passing

### Phase 1: FATAL
- [ ] Audit: 0 FATAL violations
- [ ] Violations: 203 → 169 remaining
- [ ] Tests: 523/523 pass
- [ ] git tag: audit-phase1-complete-<hash>

### Phase 2: Determinism
- [ ] 3x determinism test passes
- [ ] Violations: 169 → 82 remaining
- [ ] Tests: 523/523 pass
- [ ] git tag: audit-phase2-complete-<hash>

### Phase 3: Evidence
- [ ] Parity check: PASS
- [ ] Violations: 82 → 53 remaining
- [ ] Tests: 523/523 pass
- [ ] git tag: audit-phase3-complete-<hash>

### Phase 4: Posture
- [ ] mypy --strict: 0 errors
- [ ] Docker offline: working
- [ ] Violations: 53 → 41 remaining
- [ ] Tests: 523/523 pass
- [ ] git tag: audit-phase4-complete-<hash>

### Phase 5: Errors
- [ ] Error tests: all pass
- [ ] Coverage: ≥95%
- [ ] Violations: 41 → 0 remaining
- [ ] Tests: 523/523 pass
- [ ] git tag: audit-phase5-complete-<hash>

### Phase 6: Verification
- [ ] Final audit: 0 violations
- [ ] All gates: PASS
- [ ] Tests: 523/523 pass
- [ ] git tag: v1.0.0-audit-clean

---

## Critical Path Dependencies

**These phases MUST execute in order** (no parallel work):

```
Phase 0 (setup) ──required──> Phase 1 (FATAL removal)
                                      ↓
                              Phase 2 (Determinism)
                                      ↓
                              Phase 3 (Evidence)
                                      ↓
                              Phase 4 (Posture)
                                      ↓
                              Phase 5 (Errors)
                                      ↓
                              Phase 6 (Verification)
                                      ↓
                          🚀 PRODUCTION READY
```

**Why sequential?**
1. Phase 1 must complete first (eval/exec blocks all other work)
2. Phase 2 depends on Phase 1 fixes (seeding expects clean code)
3. Phase 3 depends on Phase 2 determinism (parity needs reproducibility)
4. Phases 4-6 build on earlier foundations

**Cannot be done in parallel** because violations in one phase affect others.

---

## Immediate Next Action (Right Now)

### **User's Next Step: 3-Minute Checklist**

1. **Read README.md** (10 minutes)
   - Location: `tasks/AV-001-authenticity-remediation/README.md`
   - Purpose: Task overview and document navigation
   - Command: `cat tasks/AV-001-authenticity-remediation/README.md | less`

2. **Read EXECUTIVE_SUMMARY.md** (5 minutes)
   - Location: `tasks/AV-001-authenticity-remediation/EXECUTIVE_SUMMARY.md`
   - Purpose: Understand violation scope and success criteria
   - Command: `cat tasks/AV-001-authenticity-remediation/EXECUTIVE_SUMMARY.md | less`

3. **Review Day 1 Morning in QUICK_START_CHECKLIST.md** (5 minutes)
   - Location: `tasks/AV-001-authenticity-remediation/QUICK_START_CHECKLIST.md`
   - Section: "Day 1: FATAL + Determinism → Morning: Phase 1"
   - Purpose: See today's tasks

4. **Execute Phase 0 Setup** (5 minutes)
   - Location: `tasks/AV-001-authenticity-remediation/REMEDIATION_PLAN.md`
   - Section: "Phase 0: Pre-remediation Setup"
   - Commands:
     ```bash
     cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
     git tag -a audit-baseline-20251026 -m "AV-001 pre-remediation baseline"
     python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json
     pytest tests/ --cov -q
     ```

5. **Begin Phase 1** (4-7 hours)
   - Start with QUICK_START_CHECKLIST.md Day 1 Morning
   - Reference REMEDIATION_PLAN.md for code examples
   - Track progress in ISSUE_TRACKER.md

---

## Risk Mitigation

### **If Phase Fails**:
```bash
# Emergency rollback to baseline
git reset --hard audit-baseline-20251026
git clean -fd

# Restart phase
# (Use diagnostic trees in TROUBLESHOOTING_GUIDE.md)
```

### **If Estimate Wrong**:
- Day 3 has 3-6 hour buffer built in
- Can extend into Day 4 if needed
- Prioritize completion over speed

### **If Stuck for 30+ Minutes**:
- Check TROUBLESHOOTING_GUIDE.md (symptom-based)
- Review REMEDIATION_PLAN.md (detailed instructions)
- Consult ISSUE_TRACKER.md (issue-specific details)

---

## Document Reference for Each Phase

| Phase | Documents | Commands |
|-------|-----------|----------|
| 0 | REMEDIATION_PLAN.md Phase 0 | git tag, audit, pytest |
| 1 | QUICK_START_CHECKLIST.md (Day 1 morning), REMEDIATION_PLAN.md Phase 1 | grep eval/exec, fixes, tests |
| 2 | QUICK_START_CHECKLIST.md (Day 1 afternoon), REMEDIATION_PLAN.md Phase 2 | FIXED_TIME/SEED, determinism test |
| 3 | QUICK_START_CHECKLIST.md (Day 2 morning), REMEDIATION_PLAN.md Phase 3 | parity check, rubric tests |
| 4 | QUICK_START_CHECKLIST.md (Day 2 afternoon), REMEDIATION_PLAN.md Phase 4 | mypy, Docker test |
| 5 | QUICK_START_CHECKLIST.md (Day 3 morning), REMEDIATION_PLAN.md Phase 5 | error tests, coverage |
| 6 | QUICK_START_CHECKLIST.md (Day 3 afternoon), REMEDIATION_PLAN.md Phase 6 | final audit, tag |

---

## Success = End of Day 3

When Day 3 afternoon is complete:

```
✅ All 203 violations resolved
✅ 523 tests passing with ≥95% coverage
✅ mypy --strict = 0 errors
✅ Determinism verified (3x identical)
✅ Docker offline working
✅ Final audit = 0 violations
✅ Tagged: v1.0.0-audit-clean
✅ Status: 🚀 PRODUCTION READY
```

---

## Summary: Next Steps Sequence

```
NOW (2025-10-26):
  ✅ Scaffolding complete
  ✅ All documents created
  ✅ Ready for Phase 0

NEXT (2025-10-27):
  1. Read overview documents (20 min)
  2. Execute Phase 0 setup (5 min)
  3. Begin Phase 1 (4-7 hours)

DAY 1 COMPLETE (end 2025-10-27):
  ✅ Phase 1-2 complete
  ✅ 121/203 violations fixed
  ✅ Tag: audit-phase2-complete-<hash>

DAY 2 COMPLETE (end 2025-10-28):
  ✅ Phase 3-4 complete
  ✅ 162/203 violations fixed
  ✅ Tag: audit-phase4-complete-<hash>

DAY 3 COMPLETE (end 2025-10-29):
  ✅ Phase 5-6 complete
  ✅ 203/203 violations fixed
  ✅ Tag: v1.0.0-audit-clean
  ✅ PRODUCTION READY 🚀
```

---

**Document**: AV-001 Execution Roadmap
**Version**: 1.0
**Created**: 2025-10-26
**Protocol**: SCA v13.8-MEA
**Status**: Ready for Phase 0 execution

**The path is clear. Begin with README.md and follow the checklist.** 📋🚀
