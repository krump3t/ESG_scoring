# Quality Enhancements — Post-AV-001

**Status**: Optional Enhancements (Non-Blocking)
**Date**: 2025-10-26
**Protocol**: SCA v13.8-MEA
**Base Release**: v1.0.0-audit-clean

---

## Overview

Following the successful completion of AV-001 authenticity remediation (0 FATAL violations, 77 WARN non-blocking), this document tracks **optional quality enhancements** to further improve code quality.

These enhancements are **NOT required** for production deployment but provide additional rigor.

---

## Enhancement 1: Code Coverage Measurement

### Objective
Measure test coverage on Critical Path (CP) modules to verify ≥95% line coverage and ≥90% branch coverage.

### Implementation

**Configuration Added**:
- Created `.coveragerc` with:
  - Source: `agents/`, `apps/`, `libs/`
  - Omit: Test files, venv, __pycache__
  - Fail threshold: 85%
  - Report format: HTML + terminal

**Command**:
```bash
pytest tests/ --cov=apps --cov=agents --cov=libs --cov-report=term-missing --cov-report=html
```

**Expected Outcome**:
- Coverage report in terminal
- HTML report in `htmlcov/` directory
- Identify uncovered lines for targeted test additions

### Status
- Configuration: ✅ COMPLETE
- Measurement: 🔄 IN PROGRESS
- Target: ≥85% overall (not blocking production)

---

## Enhancement 2: Type Checking with mypy

### Objective
Run `mypy --strict` on Critical Path (CP) modules to verify type safety and catch potential runtime errors.

### Implementation

**Configuration Verified**:
- `mypy.ini` already exists with:
  - Python version: 3.11
  - Warnings enabled: `warn_return_any`, `warn_unused_configs`
  - Third-party library stubs configured

**CP Modules for Type Checking**:
1. `apps/api/main.py` — FastAPI scoring endpoint
2. `apps/mcp_server/server.py` — MCP JSONRPC server
3. `agents/scoring/rubric_scorer.py` — Evidence-first scorer
4. `agents/scoring/rubric_loader.py` — Rubric v3 loader
5. `libs/retrieval/parity_checker.py` — Parity verification

**Command**:
```bash
# Check specific CP modules
mypy --strict apps/api/main.py
mypy --strict apps/mcp_server/server.py
mypy --strict agents/scoring/rubric_scorer.py

# Or check all CP files
mypy apps/ agents/ libs/ --exclude tests/
```

**Current Status (Initial Run)**:
```
apps/mcp_server/server.py: 4 errors found
- Missing RUBRIC_PATH attribute
- Untyped function bodies
- Missing type annotations

Target: 0 errors on CP modules
```

### Status
- Configuration: ✅ COMPLETE
- Initial scan: ✅ COMPLETE (4 errors found)
- Remediation: 📋 PENDING (not blocking production)
- Target: 0 mypy errors on CP files

---

## Enhancement 3: CP File Type Annotations

### Objective
Add comprehensive type hints to all Critical Path (CP) functions.

### Scope
Focus on files identified in `tasks/AV-001-authenticity-remediation/context/cp_paths.json`:
- `scripts/**/*.py`
- `agents/**/*.py`
- `apps/**/*.py`
- `libs/**/*.py`

### Type Annotation Standards
```python
# Function signatures
def process_evidence(
    doc_id: str,
    chunk_id: str,
    theme: str
) -> Dict[str, Any]:
    """Process evidence record with full type safety."""
    pass

# Complex types
from typing import List, Dict, Optional, Union

def score_theme(
    evidence_records: List[Dict[str, Any]],
    rubric: Dict[str, Any],
    min_quotes: int = 2
) -> Optional[Dict[str, Union[int, float]]]:
    """Score ESG theme with evidence validation."""
    pass
```

### Priority Modules
1. `agents/scoring/rubric_scorer.py`
2. `apps/api/main.py`
3. `libs/retrieval/parity_checker.py`
4. `agents/crawler/ledger.py`

### Status
- Scoped: ✅ COMPLETE
- Implementation: 📋 PENDING
- Target: 100% type-annotated CP functions

---

## Enhancement 4: Complexity & Documentation Gates

### Objective
Measure and enforce code complexity and documentation standards on CP modules.

### Tools
1. **Lizard** (Complexity Analysis):
   ```bash
   python -m lizard agents/ apps/ libs/ --CCN 10 --length 50
   ```
   - Target: CCN ≤ 10 (cyclomatic complexity)
   - Target: Function length ≤ 50 lines

2. **Interrogate** (Documentation Coverage):
   ```bash
   python -m interrogate agents/ apps/ libs/ --verbose
   ```
   - Target: ≥95% docstring coverage on CP files

### Status
- Tools: 📦 AVAILABLE (may need installation)
- Measurement: 📋 PENDING
- Enforcement: 📋 PENDING

---

## Enhancement 5: Security & Hygiene Gates

### Objective
Run security and code hygiene scanners on codebase.

### Tools
1. **detect-secrets**:
   ```bash
   detect-secrets scan --baseline .secrets.baseline
   ```
   - Prevent accidental credential commits

2. **bandit** (Security Linter):
   ```bash
   bandit -r agents/ apps/ libs/ -f json -o bandit_report.json
   ```
   - Detect security anti-patterns

### Status
- Tools: 📦 AVAILABLE (may need installation)
- Baseline: 📋 PENDING
- Scanning: 📋 PENDING

---

## Enhancement 6: CI/CD Integration

### Objective
Integrate quality gates into continuous integration pipeline.

### Proposed CI/CD Workflow
```yaml
# .github/workflows/quality-gates.yml (example)
name: Quality Gates

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Authenticity Audit
        run: python scripts/qa/authenticity_audit.py

      - name: Type Checking
        run: mypy apps/ agents/ libs/

      - name: Coverage
        run: pytest --cov --cov-fail-under=85

      - name: Complexity
        run: lizard --CCN 10 agents/ apps/ libs/

      - name: Security Scan
        run: bandit -r agents/ apps/ libs/
```

### Status
- Workflow design: ✅ COMPLETE
- Implementation: 📋 PENDING
- Integration: 📋 PENDING

---

## Timeline & Priorities

### Immediate (Non-Blocking)
1. ✅ Coverage configuration added
2. ✅ mypy configuration verified
3. 🔄 Coverage measurement in progress
4. ✅ Type check scan completed (4 errors identified)

### Short-Term (Optional)
1. Fix 4 mypy errors in CP modules
2. Add missing type annotations
3. Run Lizard complexity analysis
4. Run Interrogate documentation check

### Long-Term (Optional)
1. Integrate security scanners (bandit, detect-secrets)
2. Set up CI/CD workflow with quality gates
3. Achieve ≥95% coverage on CP modules
4. Document all CP functions with docstrings

---

## Current Quality Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **FATAL Violations** | 0 | 0 | ✅ PASS |
| **WARN Violations** | 77 | <100 | ✅ PASS |
| **Coverage (Overall)** | TBD | ≥85% | 🔄 MEASURING |
| **Coverage (CP)** | TBD | ≥95% | 📋 PENDING |
| **mypy Errors** | 4 | 0 | 📋 PENDING |
| **Type Annotations** | Partial | 100% | 📋 PENDING |
| **CCN Complexity** | TBD | ≤10 | 📋 PENDING |
| **Docstring Coverage** | TBD | ≥95% | 📋 PENDING |

---

## Key Takeaways

1. **AV-001 is complete** — 0 FATAL violations, production-ready
2. **Quality enhancements are optional** — Not blocking deployment
3. **Coverage & type checking** — Primary focus for next iteration
4. **Tooling is configured** — Ready to measure and improve
5. **CI/CD integration** — Future enhancement for automated gates

---

## Commands Reference

```bash
# Run authenticity audit
python scripts/qa/authenticity_audit.py

# Measure coverage
pytest tests/ --cov=apps --cov=agents --cov=libs --cov-report=html

# Type check CP modules
mypy apps/ agents/ libs/ --exclude tests/

# Complexity analysis
python -m lizard agents/ apps/ libs/ --CCN 10

# Documentation coverage
python -m interrogate agents/ apps/ libs/ --verbose

# Security scan
python -m bandit -r agents/ apps/ libs/
```

---

**Status**: Optional enhancements in progress
**Next**: Review coverage results when measurement completes
**Production**: Ready to deploy v1.0.0-audit-clean immediately
