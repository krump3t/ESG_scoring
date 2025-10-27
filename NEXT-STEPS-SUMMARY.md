# Next Steps Summary — What Comes After Scaffolding

**Current State**: AV-001 scaffolding 100% complete and verified
**Date**: 2025-10-26
**Next Phase**: Phase 0 (Pre-remediation setup) → Ready to execute immediately

---

## Executive Summary

The AV-001 scaffolding is **complete and ready**. The next sequence consists of **7 distinct phases** executed over **3 days**:

| Phase | Name | Duration | Violations | Status |
|-------|------|----------|-----------|--------|
| 0 | Setup | 5 min | — | ✅ Ready NOW |
| 1 | Remove eval/exec | 4-7h | 34 FATAL | ⏳ Day 1 Morning |
| 2 | Determinism | 3-5h | 87 Determinism | ⏳ Day 1 Afternoon |
| 3 | Evidence parity | 4-6h | 29 Evidence | ⏳ Day 2 Morning |
| 4 | Production posture | 3-4h | 12 Posture | ⏳ Day 2 Afternoon |
| 5 | Error handling | 2-3h | 74 Errors | ⏳ Day 3 Morning |
| 6 | Final verify | 2-3h | — | ⏳ Day 3 Afternoon |

**Total**: 14-22 hours across 3 days (2025-10-27 → 2025-10-29)

---

## Phase 0: Pre-Remediation Setup (NOW — 5 minutes)

### Execute These 3 Commands Immediately:

#### 1. Create Baseline Tag (Emergency Rollback)
```bash
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
git tag -a audit-baseline-20251026 -m "AV-001 pre-remediation baseline snapshot"
```
**Why**: Allows `git reset --hard audit-baseline-20251026` if phases fail

#### 2. Capture Baseline Violations
```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json
# Verify: Should show 203 violations
```
**Why**: Reference for comparison after each phase

#### 3. Verify All Tests Pass
```bash
pytest tests/ --cov -q
# Expected: 523 passed
```
**Why**: Ensure no regressions already present

### Phase 0 Success:
- [ ] Baseline tag created
- [ ] Baseline audit = 203 violations
- [ ] All tests = 523 passing
- **→ Ready for Phase 1**

---

## Phase 1: Remove eval() and exec() (Day 1 Morning — 4-7 hours)

### What to Fix: 34 FATAL violations
```bash
# Find them:
grep -rn "eval(" scripts/ agents/ apps/ libs/ --include="*.py"  # ~17 instances
grep -rn "exec(" scripts/ agents/ apps/ libs/ --include="*.py"  # ~14 instances
```

### How to Fix: Apply 3 patterns
- **Pattern 1A**: `eval(json_string)` → `json.loads(json_string)`
- **Pattern 1B**: `eval(formula)` → `ast.literal_eval(formula)` or safe parser
- **Pattern 1C**: `exec(code)` → direct function call

### Verify Phase 1:
```bash
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l
# MUST show: 0

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase1.json
# MUST show: 34 FATAL violations → 0
```

### Documents:
- Daily guide: `QUICK_START_CHECKLIST.md` (Day 1 Morning)
- Code examples: `REMEDIATION_PLAN.md` (Phase 1)
- Issue tracking: `ISSUE_TRACKER.md` (Priority 0)

---

## Phase 2: Determinism (Day 1 Afternoon — 3-5 hours)

### What to Fix: 87 Determinism violations
```bash
# Find unseeded randomness:
grep -rn "random\." scripts/ agents/ apps/ libs/ --include="*.py"

# Find non-deterministic time:
grep -rn "datetime\.now\|time\.time" scripts/ agents/ apps/ libs/ --include="*.py"
```

### How to Fix: Seed everything
```python
# For randomness:
from libs.utils.determinism import initialize_numpy_seed, get_seeded_random
initialize_numpy_seed()  # Call once per module
rng = get_seeded_random()  # Use for all random calls

# For time:
from libs.utils.clock import get_clock
clock = get_clock()
timestamp = clock.now()  # Uses FIXED_TIME=1729000000.0
```

### Verify Phase 2:
```bash
export FIXED_TIME=1729000000.0 SEED=42 PYTHONHASHSEED=0
bash /tmp/test_det.sh
# MUST output: ✅ DETERMINISM VERIFIED: All 3 runs identical

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase2.json
# MUST show: 87 Determinism violations → 0
```

### Documents:
- Daily guide: `QUICK_START_CHECKLIST.md` (Day 1 Afternoon)
- Code examples: `REMEDIATION_PLAN.md` (Phase 2)
- Issue tracking: `ISSUE_TRACKER.md` (Priority 1)

---

## Phase 3: Evidence Parity & Rubric (Day 2 Morning — 4-6 hours)

### What to Fix: 29 Evidence violations
Three sub-components:
1. **Rubric compliance**: ≥2 quotes per theme
2. **Parity validation**: All evidence from retrieval results
3. **Evidence contract**: Required fields present

### How to Fix:
```python
# In RubricScorer:
MIN_QUOTES_PER_THEME = 2
def score(...):
    if len(evidence) < MIN_QUOTES_PER_THEME:
        return {"stage": 0, "confidence": 0}  # Force stage 0

# In all scoring:
from libs.retrieval.parity_checker import ParityChecker
checker = ParityChecker()
report = checker.check_parity(query, evidence_ids, top_k)
if report["parity_verdict"] != "PASS":
    raise ValueError("Parity violation")
```

### Verify Phase 3:
```bash
python scripts/qa/verify_parity.py
# MUST output: PASS

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase3.json
# MUST show: 29 Evidence violations → 0
```

### Documents:
- Daily guide: `QUICK_START_CHECKLIST.md` (Day 2 Morning)
- Code examples: `REMEDIATION_PLAN.md` (Phase 3)
- Issue tracking: `ISSUE_TRACKER.md` (Priority 2)

---

## Phase 4: Production Posture (Day 2 Afternoon — 3-4 hours)

### What to Fix: 12 Posture violations
1. **Type safety**: mypy --strict errors
2. **Error handling**: Missing try/except, 404/500 responses
3. **Docker compliance**: No external network calls

### How to Fix:
```python
# Add type annotations:
def score(self, theme: str, evidence: List[dict]) -> tuple[int, float]:
    ...

# Add error handling:
try:
    with open(path) as f:
        data = json.load(f)
except FileNotFoundError:
    logger.error(f"Missing file: {path}")
    raise

# Use Mock for network calls (no real requests):
from libs.utils.http_client import MockHTTPClient
client = MockHTTPClient({...})
response = client.get(url)  # Uses mock, not network
```

### Verify Phase 4:
```bash
mypy --strict apps/ agents/ libs/ scripts/
# MUST output: 0 errors

docker run --network none esg-scorer /trace
# MUST return: 200 OK

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase4.json
# MUST show: 12 Posture violations → 0
```

### Documents:
- Daily guide: `QUICK_START_CHECKLIST.md` (Day 2 Afternoon)
- Code examples: `REMEDIATION_PLAN.md` (Phase 4)
- Issue tracking: `ISSUE_TRACKER.md` (Priority 3)

---

## Phase 5: Error Handling (Day 3 Morning — 2-3 hours)

### What to Fix: 74 Silent failure violations
- Missing error handlers
- Insufficient logging
- Silent exception swallowing

### How to Fix:
```python
# Add logging:
import logging
logger = logging.getLogger(__name__)

# In all exception blocks:
except KeyError as e:
    logger.error(f"Missing key: {e}")
    raise  # Don't silence

# Test error cases:
def test_missing_key_raises():
    with pytest.raises(KeyError):
        func({})  # Should raise, not pass silently
```

### Verify Phase 5:
```bash
pytest tests/ -k error -v
# MUST: All pass

pytest tests/ --cov=agents,apps,libs --cov-report=term | grep TOTAL
# MUST: ≥95% coverage

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase5.json
# MUST: 74 Error violations → 0
```

### Documents:
- Daily guide: `QUICK_START_CHECKLIST.md` (Day 3 Morning)
- Code examples: `REMEDIATION_PLAN.md` (Phase 5)
- Issue tracking: `ISSUE_TRACKER.md` (Priority 4)

---

## Phase 6: Final Verification (Day 3 Afternoon — 2-3 hours)

### What to Verify: All 203 violations fixed

#### 1. Complete Audit (5 min)
```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json
python -c "import json; print(f'Violations: {len(json.load(open(\"artifacts/audit_final.json\")))}')"
# MUST output: Violations: 0
```

#### 2. Full Test Suite (30 min)
```bash
pytest tests/ --cov=agents,apps,libs --cov-report=html,term
# MUST output: 523 passed, ≥95% coverage
```

#### 3. Type Safety (5 min)
```bash
mypy --strict apps/ agents/ libs/ scripts/
# MUST output: 0 errors
```

#### 4. Determinism (10 min)
```bash
export FIXED_TIME=1729000000.0 SEED=42 PYTHONHASHSEED=0
bash /tmp/test_det.sh
# MUST output: ✅ DETERMINISM VERIFIED
```

#### 5. Docker Offline (5 min)
```bash
docker run --network none esg-scorer /trace
# MUST return: 200 OK
```

#### 6. Create Completion Report (30 min)
Document:
- All 203 violations fixed
- Timeline (actual hours per phase)
- Test results
- Sign-off

#### 7. Tag and Commit (5 min)
```bash
git add .
git commit -m "chore(AV-001): Final — all 203 violations resolved"
git tag -a v1.0.0-audit-clean -m "AV-001 Production Ready"
```

### Success:
```
✅ ALL 203 VIOLATIONS RESOLVED
✅ 523/523 TESTS PASSING
✅ ≥95% COVERAGE
✅ MYPY --STRICT: 0 ERRORS
✅ 3X DETERMINISM: VERIFIED
✅ DOCKER OFFLINE: WORKING
✅ TAGGED: v1.0.0-audit-clean
✅ STATUS: 🚀 PRODUCTION READY
```

---

## The Complete Execution Path

```
RIGHT NOW (5 min)
├─ Phase 0: Setup
│  ├─ git tag baseline
│  ├─ audit capture
│  └─ verify tests
└─ Ready for Day 1

DAY 1 (7-12 hours)
├─ Morning (4-7h)
│  └─ Phase 1: Remove eval/exec (34 fixes)
├─ Afternoon (3-5h)
│  └─ Phase 2: Seed randomness (87 fixes)
└─ Checkpoint: 121/203 violations fixed

DAY 2 (7-10 hours)
├─ Morning (4-6h)
│  └─ Phase 3: Evidence parity (29 fixes)
├─ Afternoon (3-4h)
│  └─ Phase 4: Production posture (12 fixes)
└─ Checkpoint: 162/203 violations fixed

DAY 3 (3-6 hours)
├─ Morning (2-3h)
│  └─ Phase 5: Error handling (74 fixes)
├─ Afternoon (2-3h)
│  └─ Phase 6: Final verification
└─ Checkpoint: 203/203 violations fixed ✅

🚀 PRODUCTION READY
```

---

## Key Documents for Each Phase

| Phase | Daily Checklist | Detailed Guide | Issue Tracker |
|-------|-----------------|-----------------|---------------|
| 0 | N/A | REMEDIATION_PLAN.md (Phase 0) | N/A |
| 1 | QUICK_START_CHECKLIST (Day 1 Morning) | REMEDIATION_PLAN.md (Phase 1) | ISSUE_TRACKER.md (Priority 0) |
| 2 | QUICK_START_CHECKLIST (Day 1 Afternoon) | REMEDIATION_PLAN.md (Phase 2) | ISSUE_TRACKER.md (Priority 1) |
| 3 | QUICK_START_CHECKLIST (Day 2 Morning) | REMEDIATION_PLAN.md (Phase 3) | ISSUE_TRACKER.md (Priority 2) |
| 4 | QUICK_START_CHECKLIST (Day 2 Afternoon) | REMEDIATION_PLAN.md (Phase 4) | ISSUE_TRACKER.md (Priority 3) |
| 5 | QUICK_START_CHECKLIST (Day 3 Morning) | REMEDIATION_PLAN.md (Phase 5) | ISSUE_TRACKER.md (Priority 4) |
| 6 | QUICK_START_CHECKLIST (Day 3 Afternoon) | REMEDIATION_PLAN.md (Phase 6) | ISSUE_TRACKER.md (Phase 6) |

---

## What You'll Have at the End

**After Phase 0** (5 min):
✅ Immutable baseline snapshot
✅ Baseline violation count (203)
✅ Test baseline (523 passing)

**After Phase 1** (Day 1 Morning):
✅ 34 eval/exec calls removed
✅ 0 FATAL violations
✅ 121/203 violations fixed

**After Phase 2** (Day 1 Afternoon):
✅ 87 randomness operations seeded
✅ 3x identical runs verified
✅ 121/203 violations fixed

**After Phase 3** (Day 2 Morning):
✅ 29 evidence parity rules enforced
✅ Rubric MIN_QUOTES compliance active
✅ 162/203 violations fixed

**After Phase 4** (Day 2 Afternoon):
✅ Type safety: 0 mypy errors
✅ Error handling complete
✅ Docker offline working
✅ 162/203 violations fixed

**After Phase 5** (Day 3 Morning):
✅ 74 error handlers comprehensive
✅ Logging throughout
✅ Coverage ≥95%
✅ 203/203 violations fixed

**After Phase 6** (Day 3 Afternoon):
✅ Final audit: 0 violations
✅ All tests passing: 523/523
✅ All gates passing
✅ Tagged: v1.0.0-audit-clean
✅ 🚀 PRODUCTION READY

---

## Your Next Action (Right Now)

### Option A: Execute Phase 0 Immediately (5 minutes)
```bash
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
git tag -a audit-baseline-20251026 -m "AV-001 pre-remediation baseline"
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json
pytest tests/ --cov -q
```
Then verify all 3 steps pass, then proceed to Phase 1 tomorrow morning.

### Option B: Read First, Execute Tomorrow (20 minutes)
1. Read `README.md` (10 min)
2. Read `EXECUTIVE_SUMMARY.md` (5 min)
3. Review `QUICK_START_CHECKLIST.md` Day 1 Morning (5 min)
4. Tomorrow morning, execute Phase 0, then Phase 1

### Recommended: Option A
Get the 5-minute Phase 0 done right now, then you're locked in and ready to start Phase 1 tomorrow morning.

---

## Success Definition

You're done when:
```
✅ 203/203 violations fixed
✅ 523/523 tests passing
✅ ≥95% code coverage
✅ mypy --strict: 0 errors
✅ 3x determinism verified
✅ Docker offline working
✅ Final audit: 0 violations
✅ Tagged: v1.0.0-audit-clean
✅ Status: PRODUCTION READY
```

Estimated time: **14-22 hours across 3 days (2025-10-27 → 2025-10-29)**

---

**Document**: Next Steps Summary
**Version**: 1.0
**Created**: 2025-10-26
**Status**: Ready to execute

**The path is clear. Begin with Phase 0 (5 minutes right now), then follow the daily checklists.** 🚀
