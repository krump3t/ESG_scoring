# Critical Path Module Violations - Detailed Analysis

**Analysis Date**: 2025-11-04  
**Total CP Module Violations**: 11 ruff + 2 mypy = 13 total  
**Percentage of Total**: Ruff 0.1% (11/8211) | Mypy 1.8% (2/113)

## Key Finding

**CP modules are remarkably clean**: 99.9% of violations are in non-CP code.

---

## Ruff Violations (11 total)

### agents\orchestration\langgraph_orchestrator.py (4 violations)

1. **F841** (Line 212): Local variable `prompt` assigned but never used
   - Fix: Remove unused variable
   - Severity: LOW

2-4. **E501** (Lines 303, 494, 498): Line too long (89-109 chars > 88 limit)
   - Fix: Break lines
   - Severity: LOW (style only)

### agents\scoring\parity_validator.py (4 violations)

1-2. **W293** (Lines 17, 21): Blank line contains whitespace
   - Fix: Remove trailing whitespace
   - Severity: TRIVIAL

3-4. **E501** (Lines 29, 54): Line too long (91-106 chars > 88 limit)
   - Fix: Break lines
   - Severity: LOW (style only)

### libs\chunking\structure_aware_chunker.py (3 violations)

1. **C901** (Line 150): Function `_chunk_pdf_with_docling` too complex (18 > 10)
   - Fix: Refactor to reduce cyclomatic complexity OR add # noqa: C901 with justification
   - Severity: MEDIUM (affects maintainability, but function is CP-critical)
   - Note: This is the only significant violation requiring design consideration

2-3. **E501** (Lines 281, 445): Line too long (102-109 chars > 88 limit)
   - Fix: Break lines
   - Severity: LOW (style only)

---

## Mypy Errors (2 total + 3 related)

### libs\fusion\rrf_fusion.py (3 errors)

1. **Line 30**: Need type annotation for "rrf_scores"
   - Fix: Add explicit type: `rrf_scores: dict[str, float] = {}`
   - Severity: LOW

2. **Line 98**: Function `main()` missing return type annotation
   - Fix: Add `-> None`
   - Severity: LOW

3. **Line 165**: Call to untyped function "main" in typed context
   - Fix: Will auto-resolve when #2 is fixed
   - Severity: LOW (cascade)

### agents\scoring\parity_validator.py (2 errors)

1. **Line 52**: Function `main()` missing return type annotation
   - Fix: Add `-> None`
   - Severity: LOW

2. **Line 94**: Call to untyped function "main" in typed context
   - Fix: Will auto-resolve when #1 is fixed
   - Severity: LOW (cascade)

---

## Remediation Priority

### Phase R.1: Quick Wins (5 minutes)
- Remove unused variable (F841)
- Strip trailing whitespace (W293)
- Add return type annotations to main() functions
- Add type annotation to rrf_scores

### Phase R.2: Line Length Fixes (10 minutes)
- Break 7 long lines across 3 files

### Phase R.3: Complexity Reduction (30 minutes OR defer)
- Address C901 in `_chunk_pdf_with_docling`
- Options:
  1. Refactor function into smaller helpers
  2. Add # noqa: C901 with architectural justification
  3. Defer if function is stable and well-tested

**Recommendation**: Execute R.1 + R.2 immediately (15 min), defer R.3 pending architectural review.

---

## Post-Remediation Validation

After fixes, rerun:
```bash
ruff check agents/orchestration/langgraph_orchestrator.py \
            libs/chunking/structure_aware_chunker.py \
            agents/scoring/parity_validator.py \
            libs/fusion/rrf_fusion.py --select I,F,N,E,W,C901,UP

mypy --strict libs/fusion/rrf_fusion.py agents/scoring/parity_validator.py
```

Expected result: 0 ruff errors (or 1 if C901 deferred), 0 mypy errors

---

**Next Action**: Proceed with Phase R.1 + R.2 remediation
