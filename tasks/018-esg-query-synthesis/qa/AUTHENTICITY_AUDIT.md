# Authenticity Audit — Task 018 Reference Guide

**Audit ID**: AV-001-20251026
**Location**: Root-level `artifacts/authenticity/`
**Status**: Baseline captured (203 violations: 34 FATAL, 169 WARN)
**Applies To**: All production code (apps/, libs/, scripts/, agents/)

---

## Quick Navigation

| Need | File | Purpose |
|------|------|---------|
| **Overview** | [README.md](../../artifacts/authenticity/README.md) | User guide, usage patterns, troubleshooting |
| **Executive Summary** | [ANALYSIS_REPORT.md](../../artifacts/authenticity/ANALYSIS_REPORT.md) | Findings, impact assessment, remediation strategies |
| **Implementation Details** | [IMPLEMENTATION_SUMMARY.md](../../artifacts/authenticity/IMPLEMENTATION_SUMMARY.md) | What was built, architecture, statistics |
| **Violation List (JSON)** | [report.json](../../artifacts/authenticity/report.json) | Machine-readable (file:line references) |
| **Violation List (Markdown)** | [report.md](../../artifacts/authenticity/report.md) | Human-readable (organized by type) |
| **Baseline Snapshot** | [BASELINE_SNAPSHOT.json](../../artifacts/authenticity/BASELINE_SNAPSHOT.json) | Pre-remediation state (for comparison) |
| **Remediation Guide** | [REMEDIATION_LOG.md](../../artifacts/authenticity/REMEDIATION_LOG.md) | Violation-by-violation fix templates |
| **Rollback Procedures** | [REVERT_PLAYBOOK.md](../../artifacts/authenticity/REVERT_PLAYBOOK.md) | Git-based recovery & selective revert |

---

## For Task 018 Developers

### What This Means for Your Implementation

As you work on Phase 3 (ESG Query Synthesis), ensure new code:

✓ **Avoids eval/exec** — Use explicit routing instead of dynamic code execution
✓ **Controls time calls** — Use environment variable overrides (AUDIT_TIME) for datetime.now()
✓ **Logs exceptions** — Add logger calls instead of silent `except: pass` blocks
✓ **Deterministic ordering** — Use `sorted()` in dict iterations
✓ **No unseeded random** — Set SEED=42 or use deterministic alternatives

### Example: Phase 3 Code Compliance

```python
# ❌ WRONG: Non-compliant patterns
def get_timestamp():
    return datetime.now().isoformat()  # Non-deterministic

def route_handler(operation):
    return eval(f"handle_{operation}()")  # eval/exec violation

# ✅ CORRECT: SCA v13.8 compliant
def get_timestamp():
    """Get timestamp, respecting AUDIT_TIME override for determinism."""
    return os.getenv("AUDIT_TIME", datetime.now().isoformat())

def route_handler(operation):
    handlers = {
        "query_synthesis": query_synthesis,
        "ranking": ranking,
        "confidence": confidence,
    }
    return handlers[operation]()
```

---

## Baseline Audit Results

### Violations Summary

```
Total: 203 violations
├─ FATAL (blocks validation): 34
│  └─ eval/exec usage in scripts/
│
└─ WARN (affects reproducibility): 169
   ├─ 76 non-deterministic time calls
   ├─ 74 silent exception handlers
   ├─ 8 JSON-as-Parquet patterns
   ├─ 9 dict iteration ordering
   └─ 2 unseeded random calls
```

### Top 3 Priorities for Remediation

1. **eval/exec Removal (34 FATAL)** — 2-4 hours
   - Location: primarily in scripts/ utilities
   - Blocker for phase validation
   - See ANALYSIS_REPORT.md § "eval/exec() Usage"

2. **Time Overrides (76 WARN)** — 1-2 hours
   - Location: apps/evaluation/, apps/ingestion/, apps/scoring/
   - Required for determinism proof
   - See ANALYSIS_REPORT.md § "Non-Deterministic Time"

3. **Exception Logging (74 WARN)** — 1 hour
   - Location: validator.py, report_fetcher.py, hybrid_retriever.py
   - Improves observability
   - See ANALYSIS_REPORT.md § "Silent Exception Handling"

---

## Running the Audit Yourself

### Quick Test

```bash
cd ../../..  # Go to ESG_ROOT
export PYTHONHASHSEED=0 SEED=42

# Run audit
python scripts/qa/authenticity_audit.py --root . --out artifacts/authenticity

# Expected output
# Total Violations: 203
# FATAL: 34
# WARN: 169
# Status: BLOCKED
```

### Run Tests

```bash
pytest tests/test_authenticity_audit.py -v --cov
# Expected: 28 tests pass, ≥95% coverage
```

### Track Progress During Remediation

After each fix:
```bash
python scripts/qa/authenticity_audit.py --root . --out artifacts/authenticity
# Check: Do FATAL counts decrease?
grep "FATAL" artifacts/authenticity/report.md | wc -l
```

---

## Cross-References

### Related Documents
- **Root-level summary**: [AUTHENTICITY_AUDIT_COMPLETE.md](../../AUTHENTICITY_AUDIT_COMPLETE.md)
- **Audit implementation**: [scripts/qa/authenticity_audit.py](../../scripts/qa/authenticity_audit.py)
- **Test suite**: [tests/test_authenticity_audit.py](../../tests/test_authenticity_audit.py)

### Task-Level Documentation
- **Task 018 hypothesis**: [context/hypothesis.md](../context/hypothesis.md)
- **Task 018 design**: [context/design.md](../context/design.md)

---

## Key Insight: Determinism Requirement

The audit exists to prove that given:
- Same input data
- SEED=42 (environment)
- PYTHONHASHSEED=0

The pipeline produces **identical outputs** on repeated runs (same SHA256 hashes).

**This is non-negotiable for Phase validation under SCA v13.8.**

---

## Common Questions

**Q: Does my Phase 3 code need to be audit-compliant?**
A: Yes. Follow the patterns above. New violations will block your phase validation.

**Q: What if I need eval/exec for something?**
A: Document the exception. Audit supports exemptions via `exemption` field in Violation. But generally: there's always a better way (explicit routing, config, etc.).

**Q: How do I know if determinism is working?**
A: Run pipeline twice with SEED=42, compare artifact hashes. Should be identical.

**Q: Can I use datetime.now() in my code?**
A: Yes, but add override support:
  ```python
  ts = os.getenv("AUDIT_TIME", datetime.now().isoformat())
  ```

**Q: Where's the full remediation plan?**
A: See [REMEDIATION_LOG.md](../../artifacts/authenticity/REMEDIATION_LOG.md) for templates and [ANALYSIS_REPORT.md](../../artifacts/authenticity/ANALYSIS_REPORT.md) for detailed strategies.

---

## Audit Files Checklist

When implementing Phase 3, verify you haven't introduced new violations:

- [ ] No `import requests`, `import httpx`, `import boto3` in production code
- [ ] No `random.choice()`, `numpy.random.shuffle()` without seeding
- [ ] No `datetime.now()` or `time.time()` without override mechanism
- [ ] No bare `except: pass` blocks (add logging or raise)
- [ ] No `eval()` or `exec()` calls
- [ ] No `dict.items()` iteration without `sorted()`
- [ ] Use Parquet for data artifacts, not JSON

---

**Last Updated**: 2025-10-26
**Baseline Commit**: c8798c56fd71826c7cb0093d9f3c65a68059926c
**Status**: Ready for remediation & Phase 3 implementation

For full details, see: [README.md](../../artifacts/authenticity/README.md)
