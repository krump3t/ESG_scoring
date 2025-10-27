# AV-001: Comprehensive Remediation Plan — Detailed Reference Guide

**Generated**: 2025-10-26
**Protocol**: SCA v13.8-MEA
**Total Violations**: 203 (34 FATAL, 87 Determinism, 29 Evidence, 12 Posture, 74 Errors)
**Estimated Duration**: 14-22 hours across 3 days

---

## How to Use This Document

**This is the detailed reference guide for remediation.** Use it when:
- You need code examples for a fix
- You want to understand why a violation is critical
- You need test commands to verify a fix
- You're troubleshooting a specific issue

**For daily tasks**, use QUICK_START_CHECKLIST.md instead.
**For high-level overview**, use EXECUTIVE_SUMMARY.md.
**For progress tracking**, use ISSUE_TRACKER.md.

---

## Phase 0: Pre-Remediation Setup (5 minutes)

### Step 0.1: Create Baseline Git Tag
```bash
cd prospecting-engine
git status  # Ensure clean working directory
git tag -a audit-baseline-20251026 -m "AV-001 pre-remediation baseline snapshot"
git log -1 --oneline  # Verify tag applied
```

**Why**: Allows emergency rollback if Phase 1-5 fail catastrophically.

### Step 0.2: Capture Baseline Audit
```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json
# Parse results
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
# Expected output:
# Total violations: 203
# By severity: {0: 34, 1: 87, 2: 29, 3: 12, 4: 74}
```

### Step 0.3: Verify Test Suite Baseline
```bash
pytest tests/ --cov -q
# Expected: 523 passed in X.XXs
```

**If tests are not passing**: Stop. Fix failing tests first (outside AV-001 scope).

---

## Phase 1: Remove eval() and exec() — FATAL Violations (34 issues)

### Why This Phase First?

eval() and exec() are security anti-patterns that:
1. Allow arbitrary code execution (security risk)
2. Make static analysis impossible (compliance risk)
3. Block code understanding by auditors (regulatory risk)

**FATAL violations block all subsequent phases because code won't parse/run properly.**

### Phase 1.1: Locate All eval() Instances

```bash
# Find all eval calls
grep -rn "eval(" scripts/ agents/ apps/ libs/ --include="*.py" > /tmp/eval_list.txt
echo "Total eval() calls:"
wc -l /tmp/eval_list.txt

# Example output:
# scripts/crawler.py:42:    result = eval(expression)
# agents/extraction/extractor.py:120:    value = eval(f"math.{formula}")
# ...
# Total: 17 calls
```

**Document each finding in ISSUE_TRACKER.md (F001-F034 range for eval).**

### Phase 1.2: Locate All exec() Instances

```bash
# Find all exec calls
grep -rn "exec(" scripts/ agents/ apps/ libs/ --include="*.py" > /tmp/exec_list.txt
echo "Total exec() calls:"
wc -l /tmp/exec_list.txt

# Typical result: 14-17 calls
```

**Document each finding in ISSUE_TRACKER.md.**

### Phase 1.3: Fix Strategy by Pattern

#### Pattern 1A: eval(JSON-like string)
**Symptom**: `data = eval(json_string)` or `data = eval(dict_string)`

**Before**:
```python
def load_config(config_str):
    return eval(config_str)  # ❌ Security risk, non-deterministic

config = load_config('{"key": "value"}')
```

**After**:
```python
import json

def load_config(config_str):
    return json.loads(config_str)  # ✅ Safe, deterministic

config = load_config('{"key": "value"}')
```

**Test**:
```bash
pytest tests/ -k config -v  # Verify config loading works
```

#### Pattern 1B: eval(arithmetic expression)
**Symptom**: `result = eval(formula_string)`

**Before**:
```python
def compute_score(formula, value):
    return eval(formula)  # ❌ Unsafe expression evaluation

score = compute_score("x * 2 + 1", x=5)  # Expects x to be in scope
```

**After**:
```python
from ast import literal_eval
import operator

def compute_score(formula, **kwargs):
    # Option 1: Simple cases (literals only)
    return literal_eval(formula) if formula.isdigit() else None

    # Option 2: Safe expression parser (for more complex cases)
    # Use a library like simpleeval
    # from simpleeval import simple_eval
    # return simple_eval(formula, names=kwargs)

score = compute_score("5")  # ✅ Safe
```

**Test**:
```bash
pytest tests/scoring/ -k compute -v
```

#### Pattern 1C: exec(code as string)
**Symptom**: `exec(template_string)` or `exec(script_string)`

**Before**:
```python
def run_template(template_code):
    local_vars = {}
    exec(template_code, {}, local_vars)  # ❌ Arbitrary code execution
    return local_vars

result = run_template("x = 2 + 2; y = x * 3")
```

**After**:
```python
# Option 1: Direct function call (if template is known at compile time)
def run_template_direct():
    x = 2 + 2
    y = x * 3
    return {"x": x, "y": y}

# Option 2: Jinja2 templating (for dynamic templates)
from jinja2 import Template
def run_template(template_str):
    t = Template(template_str)
    return t.render(x=2)

result = run_template_direct()
```

**Test**:
```bash
pytest tests/pipeline/ -k template -v
```

### Phase 1.4: Batch Fixes and Testing

**Process for each fix**:

1. **Locate the code**:
   ```bash
   grep -n "eval\|exec" scripts/crawler.py
   ```

2. **Apply fix** using patterns above

3. **Run minimal tests**:
   ```bash
   pytest tests/ -k crawler --tb=short -v
   ```

4. **Commit**:
   ```bash
   git add scripts/crawler.py
   git commit -m "fix(AV-001-F001): Remove eval() in crawler.py:42"
   ```

5. **Update ISSUE_TRACKER.md**: Mark F001 as ✅ DONE

6. **Repeat** for next instance

### Phase 1.5: Verify Phase 1 Complete

```bash
# No eval or exec should remain
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l
# Expected: 0

# Run full test suite
pytest tests/ --cov -q
# Expected: 523 passed

# Update audit
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase1.json

# Check violation count
python -c "
import json
before = len(json.load(open('artifacts/audit_baseline.json')))
after = len(json.load(open('artifacts/audit_after_phase1.json')))
print(f'Violations: {before} → {after} (fixed {before-after})')
"
# Expected: 203 → 169 (fixed 34)
```

---

## Phase 2: Determinism — Seed All Randomness (87 issues)

### Why Determinism?

**Regulatory requirement**: Auditors must be able to run the scoring again and get the SAME result.
**Without determinism**: Non-reproducible results = no compliance, no trust.

### Phase 2.1: Identify Unseeded Randomness

```bash
# Find random() calls
grep -rn "random\." scripts/ agents/ apps/ libs/ --include="*.py" \
  | grep -v "seed\|SEED" | head -20

# Find numpy random
grep -rn "np\.random\|numpy\.random" scripts/ agents/ apps/ libs/ --include="*.py" | head -20

# Find shuffling without seed
grep -rn "shuffle\|sample" scripts/ agents/ apps/ libs/ --include="*.py" | head -20
```

### Phase 2.2: Identify Non-Deterministic Time

```bash
# Find direct time calls
grep -rn "datetime\.now\|time\.time" scripts/ agents/ apps/ libs/ --include="*.py" | head -20
```

### Phase 2.3: Fix Pattern 2A — Random Calls

**Before**:
```python
import random

def select_items(items):
    return random.sample(items, k=5)  # ❌ Non-deterministic

def shuffle_data(data):
    random.shuffle(data)  # ❌ Modifies in-place
    return data
```

**After**:
```python
from libs.utils.determinism import get_seeded_random, initialize_numpy_seed

def __init__(self):
    initialize_numpy_seed()  # Call once at module init

def select_items(self, items):
    rng = get_seeded_random()
    return rng.sample(items, k=5)  # ✅ Seeded

def shuffle_data(self, data):
    rng = get_seeded_random()
    shuffled = data.copy()
    rng.shuffle(shuffled)
    return shuffled  # ✅ Non-destructive
```

**Test**:
```python
# Test determinism
from libs.utils.determinism import initialize_numpy_seed

def test_select_items_deterministic():
    obj1 = MyClass()
    items1 = obj1.select_items([1, 2, 3, 4, 5])

    obj2 = MyClass()
    items2 = obj2.select_items([1, 2, 3, 4, 5])

    assert items1 == items2  # ✅ Same seed, same result
```

### Phase 2.4: Fix Pattern 2B — Time Operations

**Before**:
```python
from datetime import datetime

def log_event(event_name):
    timestamp = datetime.now().isoformat()
    return {"event": event_name, "time": timestamp}  # ❌ Changes every time
```

**After**:
```python
from libs.utils.clock import get_clock

def log_event(self, event_name):
    clock = get_clock()
    timestamp = clock.now().isoformat()
    return {"event": event_name, "time": timestamp}  # ✅ FIXED_TIME env var

# In environment:
# export FIXED_TIME=1729000000.0
# Now all calls return same timestamp
```

### Phase 2.5: Fix Pattern 2C — Temperature/Top-P Randomness in LLM

**Before**:
```python
def query_llm(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        prompt=prompt,
        temperature=0.7,  # ❌ Randomness not seeded
        top_p=0.9
    )
    return response
```

**After**:
```python
from libs.utils.determinism import get_seeded_random

def query_llm(self, prompt):
    rng = get_seeded_random()
    # Use seed to control temperature/top_p
    effective_temp = 0.7  # Could be seeded if randomized

    response = openai.ChatCompletion.create(
        model="gpt-4",
        prompt=prompt,
        temperature=effective_temp,
        top_p=0.9,
        seed=42  # ✅ Add explicit seed
    )
    return response
```

### Phase 2.6: Determinism Verification

**Create determinism test**:
```bash
cat > /tmp/test_det.sh << 'EOFSCRIPT'
#!/bin/bash

export FIXED_TIME=1729000000.0
export SEED=42
export PYTHONHASHSEED=0

cd prospecting-engine

# Run 1
python evaluate.py > /tmp/run1.json 2>/dev/null
SHA1=$(sha256sum /tmp/run1.json | awk '{print $1}')

# Run 2
python evaluate.py > /tmp/run2.json 2>/dev/null
SHA2=$(sha256sum /tmp/run2.json | awk '{print $1}')

# Run 3
python evaluate.py > /tmp/run3.json 2>/dev/null
SHA3=$(sha256sum /tmp/run3.json | awk '{print $1}')

# Check
if [[ "$SHA1" == "$SHA2" ]] && [[ "$SHA2" == "$SHA3" ]]; then
    echo "✅ DETERMINISM VERIFIED: All 3 runs identical"
    echo "SHA256: $SHA1"
    exit 0
else
    echo "❌ DETERMINISM FAILED: Runs differ"
    echo "Run 1: $SHA1"
    echo "Run 2: $SHA2"
    echo "Run 3: $SHA3"
    exit 1
fi
EOFSCRIPT

chmod +x /tmp/test_det.sh
bash /tmp/test_det.sh
```

**Expected output**:
```
✅ DETERMINISM VERIFIED: All 3 runs identical
SHA256: abc123def456...
```

### Phase 2.7: Verify Phase 2 Complete

```bash
# Run determinism test
bash /tmp/test_det.sh
# Expected: ✅ DETERMINISM VERIFIED

# Run full test suite
pytest tests/ --cov -q
# Expected: 523 passed

# Audit check
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase2.json
python -c "
import json
b4 = len(json.load(open('artifacts/audit_after_phase1.json')))
aft = len(json.load(open('artifacts/audit_after_phase2.json')))
print(f'Violations: {b4} → {aft} (fixed {b4-aft})')
"
# Expected: 169 → 82 (fixed 87)
```

---

## Phase 3: Evidence Parity & Rubric Compliance (29 issues)

### Phase 3.1: Rubric Compliance (MIN_QUOTES)

**Requirement**: All scoring must be backed by ≥2 verbatim quotes from documents.

**Before**:
```python
def score(theme, evidence):
    if len(evidence) == 0:
        return {"stage": 0, "confidence": 0}
    elif len(evidence) >= 1:
        return {"stage": 2, "confidence": 0.5}  # ❌ Allows 1 quote
```

**After**:
```python
MIN_QUOTES_PER_THEME = 2

def score(theme, evidence):
    if len(evidence) < MIN_QUOTES_PER_THEME:
        return {"stage": 0, "confidence": 0}  # Enforce minimum
    elif len(evidence) >= MIN_QUOTES_PER_THEME:
        # Calculate stage based on quote quality
        return {"stage": 2, "confidence": 0.5}  # ✅ Requires ≥2 quotes
```

### Phase 3.2: Parity Validation (evidence ⊆ top-k)

**Requirement**: All evidence must come from retrieval results.

**Before**:
```python
def score_with_evidence(query, evidence_docs, top_k_from_retrieval):
    # evidence_docs could contain docs NOT in top_k ❌ Parity violation
    score = calculate_score(evidence_docs)
    return score
```

**After**:
```python
from libs.retrieval.parity_checker import ParityChecker

def score_with_evidence(self, query, evidence_ids, top_k_results):
    # Validate parity
    checker = ParityChecker()
    report = checker.check_parity(
        query=query,
        evidence_ids=evidence_ids,
        fused_top_k=top_k_results,
        k=10
    )

    if report["parity_verdict"] != "PASS":
        raise ValueError(f"Parity violation: {report}")  # ✅ Enforce

    # Safe to score
    score = calculate_score(evidence_ids)
    return score
```

**Test**:
```python
def test_parity_violation_raises():
    evidence = ["doc5", "doc7"]  # doc7 not in retrieval
    top_k = ["doc1", "doc2", "doc5"]

    with pytest.raises(ValueError):
        score_with_evidence("query", evidence, top_k)
```

### Phase 3.3: Evidence Contract Validation

**Required fields in each evidence record**:
- `extract_30w` (30-word excerpt)
- `doc_id` (document identifier)
- `theme_code` (e.g., "Climate", "Social")

**Before**:
```python
evidence = {
    "extract": "Some text",  # ❌ Wrong field name
    "id": "doc1"  # ❌ Missing doc_id
}
```

**After**:
```python
from pydantic import BaseModel

class EvidenceRecord(BaseModel):
    extract_30w: str
    doc_id: str
    theme_code: str
    # Can add more fields

# Validate
evidence = EvidenceRecord(
    extract_30w="30-word text...",
    doc_id="doc1",
    theme_code="Climate"
)
```

### Phase 3.4: Verify Phase 3 Complete

```bash
pytest tests/retrieval/ -k parity -v
pytest tests/scoring/ -k rubric -v

python scripts/qa/verify_parity.py
# Expected: PASS

pytest tests/ --cov -q
# Expected: 523 passed

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase3.json
```

---

## Phase 4: Production Posture (12 issues)

### Phase 4.1: Type Safety (mypy --strict)

```bash
mypy --strict apps/ agents/ libs/ scripts/ > /tmp/mypy.txt 2>&1
cat /tmp/mypy.txt | head -20
```

**Common errors and fixes**:

| Error | Before | After |
|-------|--------|-------|
| Missing return type | `def func():` | `def func() -> str:` |
| Implicit Any | `result = func()` | `result: str = func()` |
| Optional not marked | `if x is None:` | `def func(x: Optional[str]):` |
| Union required | `x: int or str` | `x: Union[int, str]` |

```bash
# Example fix
# Before:
def assess_evidence(theme, evidence):
    return quality_score

# After:
def assess_evidence(self, theme: str, evidence: List[dict]) -> tuple[int, float]:
    return (stage, confidence)
```

### Phase 4.2: Docker Offline Compliance

**Requirement**: No external network calls during scoring.

```bash
# Check for network calls
grep -r "requests\|urllib\|socket\|http\.client" apps/ agents/ libs/ --include="*.py" \
  | grep -v "Mock\|mock\|test" | wc -l
# Expected: 0
```

**Fix pattern**:
```python
# Before:
import requests
response = requests.get("https://api.example.com/data")  # ❌ Network call

# After:
from libs.utils.http_client import get_http_client
client = get_http_client()
response = client.get("https://api.example.com/data")  # ✅ MockHTTPClient in tests
```

### Phase 4.3: Verify Phase 4 Complete

```bash
mypy --strict apps/ agents/ libs/ scripts/
# Expected: 0 errors

docker run --network none esg-scorer /trace
# Expected: 200 OK

pytest tests/ --cov -q
# Expected: 523 passed

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase4.json
```

---

## Phase 5: Error Handling (74 issues)

### Phase 5.1: Silent Failure Detection

```bash
# Find all except blocks
grep -rn "except" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l
# Expected: ~100+ blocks

# Check for except: pass (silent failures)
grep -rn "except.*:\s*$" scripts/ agents/ apps/ libs/ --include="*.py" | head -10
```

### Phase 5.2: Fix Pattern 5A — Add Logging

**Before**:
```python
def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        pass  # ❌ Silent failure
```

**After**:
```python
import logging
logger = logging.getLogger(__name__)

def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        raise  # ✅ Re-raise, don't silent
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        raise
```

### Phase 5.3: Verify Phase 5 Complete

```bash
# Check error handling in tests
pytest tests/ -k error -v
# Expected: All pass

# Coverage check
pytest tests/ --cov=agents,apps,libs --cov-report=term | grep TOTAL
# Expected: ≥95%

pytest tests/ --cov -q
# Expected: 523 passed

python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase5.json
```

---

## Phase 6: Final Verification

### Phase 6.1: Complete Audit

```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json

python -c "
import json
data = json.load(open('artifacts/audit_final.json'))
print(f'Total violations: {len(data)}')
if len(data) == 0:
    print('✅ ALL VIOLATIONS RESOLVED')
else:
    print('❌ Remaining violations:')
    for v in data[:5]:
        print(f\"  {v['violation_id']}: {v['file_path']}:{v['line_number']}\")
"
# Expected: Total violations: 0
```

### Phase 6.2: Final Test Run

```bash
pytest tests/ --cov=agents,apps,libs,scripts --cov-report=html,term
# Expected: 523 passed, ≥95% coverage
```

### Phase 6.3: Final Type Check

```bash
mypy --strict apps/ agents/ libs/ scripts/
# Expected: 0 errors
```

### Phase 6.4: Final Determinism Check

```bash
bash /tmp/test_det.sh
# Expected: ✅ DETERMINISM VERIFIED
```

### Phase 6.5: Final Docker Test

```bash
docker run --network none esg-scorer /trace
# Expected: 200 OK with gate verdicts
```

### Phase 6.6: Create Completion Report

```bash
cat > tasks/AV-001-authenticity-remediation/COMPLETION_REPORT.md << 'EOF'
# AV-001 Completion Report

## Summary
- **Total Violations Fixed**: 203/203 (100%)
- **Timeline**: [Actual duration]
- **Status**: ✅ PRODUCTION READY

## Verification Results
- Audit: 0 violations
- Tests: 523/523 pass
- Coverage: ≥95%
- Type Safety: mypy --strict = 0 errors
- Determinism: 3x identical runs
- Docker Offline: ✅ PASS

## Sign-Off
All authenticity gates verified. System is production-ready.
EOF
```

### Phase 6.7: Final Commits and Tagging

```bash
git add .
git commit -m "fix(AV-001): Complete Phase 6 verification — all 203 violations resolved"
git tag -a v1.0.0-audit-clean -m "AV-001 Complete — Production Ready"
git log --oneline | head -20  # Verify commit history
```

---

## Appendix A: Quick Reference Commands

```bash
# Setup
git tag -a audit-baseline-20251026 -m "Pre-remediation"
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json

# Phase 1: Remove eval/exec
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l

# Phase 2: Determinism
export FIXED_TIME=1729000000.0 SEED=42
bash /tmp/test_det.sh

# Phase 3: Parity + Rubric
python scripts/qa/verify_parity.py

# Phase 4: Posture
mypy --strict apps/ agents/ libs/
docker run --network none esg-scorer /trace

# Phase 5-6: Testing
pytest tests/ --cov
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json

# Verification
grep -c '"violation_id"' artifacts/audit_final.json  # Should be 0
```

---

## Appendix B: Troubleshooting

**Problem**: Tests failing after Phase 1 fixes
**Solution**: The fix broke a dependent function. Check test error message, update all call sites.

**Problem**: Determinism test shows different hashes
**Solution**: Some code path still using non-deterministic operations. Run 3x with same SEED, identify diff.

**Problem**: Parity validation too strict
**Solution**: May indicate retrieval is missing relevant documents. Check retrieval algorithm.

---

**Document**: AV-001 Comprehensive Remediation Plan
**Version**: 1.0
**Created**: 2025-10-26
**Protocol**: SCA v13.8-MEA

