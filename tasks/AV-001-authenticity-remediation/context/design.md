# AV-001 Authenticity Audit Remediation — Design & Verification Strategy

**Task**: Systematically remediate 203 authenticity violations across 6 phases
**Protocol**: SCA v13.8-MEA
**Strategy**: Sequential phase execution with validation gates between phases

---

## Data Strategy

### Violation Source & Integrity

**Audit Data**:
- **Source**: `python scripts/qa/authenticity_audit.py` (canonical SCA audit tool)
- **Output**: 203 violations categorized by severity (0-4) and type
- **Storage**: `artifacts/audit_report.json` (immutable baseline)
- **Refresh**: Run audit baseline (2025-10-26) before and after each phase

**Tracking**:
- **Primary tracker**: `ISSUE_TRACKER.md` (manually updated as issues fixed)
- **Artifacts**: All remediation commits tagged with issue IDs
- **Verification**: Each phase ends with re-run of audit to confirm violation count reduction

### Data Normalization

**Violation Records** (from audit output):
```json
{
  "violation_id": "F001",
  "severity": 0,
  "type": "FATAL",
  "category": "eval_exec",
  "file_path": "scripts/crawler.py",
  "line_number": 42,
  "code_snippet": "result = eval(expression)",
  "remediation": "Use ast.literal_eval() or direct parsing",
  "estimated_effort": "10 min"
}
```

**Normalized across phases**:
- Phase 1: Filter by severity=0 (FATAL)
- Phase 2: Filter by type="DETERMINISM"
- Phase 3: Filter by type="EVIDENCE"
- Phase 4: Filter by type="POSTURE"
- Phase 5: Filter by type="ERRORS"
- Phase 6: Aggregate all phases + final verification

### Leakage Guards

**Prevents data leakage between phases**:
1. **Immutable baseline**: Git tag `audit-baseline-20251026` locks pre-remediation state
2. **Phase isolation**: Work on only violations for current phase (don't fix ahead)
3. **Test independence**: Failure-path tests isolated from success-path tests
4. **Determinism isolation**: Seeding tests use dedicated fixtures (no cross-test state)
5. **Evidence validation**: Real ESG data (Apple, Microsoft) separate from synthetic fixtures

---

## Verification Plan

### Differential Testing (Before/After Each Phase)

**Protocol**: Run audit before and after each phase, compare violation counts

**Phase 1 (FATAL)**:
```bash
# Before Phase 1
python scripts/qa/authenticity_audit.py > artifacts/audit_before_phase1.json
# Expected: Total violations = 203, FATAL violations = 34

# Execute Phase 1 fixes (all eval/exec removals)
# ... (commit work)

# After Phase 1
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase1.json
# Expected: Total violations ≈ 169, FATAL violations = 0
# ✅ Success: 34 violations resolved, no regressions
```

**Repeat for Phase 2-5**: Same differential pattern, increasing success threshold each phase

**Phase 6 (Final)**:
```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json
# Expected: Total violations = 0, all gates = PASS
```

### Sensitivity Testing (Determinism Phase)

**Phase 2 sensitivity**: Verify 3x identical runs produce byte-identical outputs

```bash
# Run 1: FIXED_TIME=1729000000.0 SEED=42
export FIXED_TIME=1729000000.0 SEED=42
python evaluate.py > run1.json
sha256sum run1.json > run1.sha256

# Run 2: Identical environment
export FIXED_TIME=1729000000.0 SEED=42
python evaluate.py > run2.json
sha256sum run2.json > run2.sha256

# Run 3: Identical environment
export FIXED_TIME=1729000000.0 SEED=42
python evaluate.py > run3.json
sha256sum run3.json > run3.sha256

# Verify
diff run1.sha256 run2.sha256  # ✅ Identical
diff run2.sha256 run3.sha256  # ✅ Identical
```

### Parity Validation (Evidence Phase)

**Phase 3 gate**: Verify all evidence used in scoring comes from retrieval results

```python
# Test scenario
retrieval_results = ["doc1", "doc3", "doc5", "doc2", "doc4"]
evidence_used = ["doc1", "doc3", "doc5"]

# Validation
parity_checker = ParityChecker()
result = parity_checker.check_parity(
    query="climate",
    evidence_ids=evidence_used,
    fused_top_k=retrieval_results,
    k=5
)
assert result["parity_verdict"] == "PASS"
```

### Failure-Path Testing (Error Handling Phase)

**Phase 5 validation**: Ensure all error conditions properly handled

```python
# Example: Missing rubric file
@pytest.mark.cp
def test_missing_rubric_error():
    scorer = RubricScorer()
    with pytest.raises(FileNotFoundError):
        scorer.score("Climate", [], org_id="test", year=2024)
    # ✅ Error propagated, not silenced
```

---

## Success Thresholds

### Phase-Specific Thresholds

| Phase | Metric | Threshold | Verification |
|-------|--------|-----------|--------------|
| 1 | FATAL violations | 0/34 | `grep -r "eval\|exec"` = 0 |
| 2 | Determinism | 3x identical | SHA256 hashes match |
| 3 | Evidence parity | 100% | `ParityChecker.check_parity()` = PASS |
| 3 | Rubric compliance | ≥2 quotes | RubricScorer enforces minimum |
| 4 | Type safety | 0 errors | `mypy --strict` = 0 |
| 5 | Error handling | All exceptions | `grep -c "except.*:" scripts/ agents/` |
| 6 | Overall | 0 violations | `authenticity_audit.py` = PASS all gates |

### Quality Gates (End-to-End)

```
✅ Pytest: 523/523 tests passing
✅ Coverage: ≥95% on modified files
✅ Type safety: mypy --strict = 0 errors
✅ Complexity: Lizard CCN ≤ 10
✅ Documentation: Interrogate ≥95%
✅ Determinism: 3x identical runs
✅ Docker offline: No network calls
```

---

## Mitigation Strategies

### Strategy 1: Phase Isolation (Prevents Cascading Failures)

**Design**: Each phase targets specific violation category
- Phase 1: Only eval/exec removals
- Phase 2: Only seeding/determinism fixes
- Phase 3: Only evidence/parity/rubric changes
- Phase 4: Only error handling improvements
- Phase 5: Only logging/monitoring additions

**Benefit**: Failures in Phase 3 don't require re-doing Phase 1 fixes

**Implementation**: Use ISSUE_TRACKER to mark phase boundaries in commits

### Strategy 2: Rollback Capability (Fast Recovery)

**Baseline snapshot**: `git tag audit-baseline-20251026`
```bash
# Emergency rollback (if multiple phases fail)
git reset --hard audit-baseline-20251026
git clean -fd
```

**Phase-level checkpoints**: After Phase 1, 2, 3 completion, create intermediate snapshots
```bash
git tag audit-phase1-complete-<commit-hash>
git tag audit-phase2-complete-<commit-hash>
```

**Test-driven rollback**: Always run full test suite before committing (prevents bad commits)

### Strategy 3: Risk-Ranked Remediation (Highest Priority First)

**Execution order** (by risk impact):
1. **Phase 1 (FATAL)**: Blocking all compliance (highest risk)
2. **Phase 2 (Determinism)**: Required for reproducibility (high risk)
3. **Phase 3 (Evidence)**: Regulatory requirement (medium-high risk)
4. **Phase 4 (Posture)**: Production readiness (medium risk)
5. **Phase 5 (Errors)**: Robustness (medium risk)
6. **Phase 6 (Verify)**: Closure & documentation (low risk)

**Rationale**: Fixes highest-risk issues first; if time runs short, core authenticity is guaranteed

### Strategy 4: Real-Data Validation (Authenticity Check)

**Phase 3 & 4 validation**: Use real company ESG reports (not mocks)

**Real sources**:
- **Apple Inc**: `https://s26.q4cdn.com/869488222/files/doc_news/2024/`
- **Microsoft Corp**: `https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RW...`
- **LSE/Bloomberg**: Real ticker lookup data

**Benefit**: Validates fixes work with actual ESG claims, not synthetic data

---

## Artifact Management

### Generated During Remediation

**Phase 1-5 artifacts**:
- `artifacts/audit_before_phase_N.json` - Baseline violations
- `artifacts/audit_after_phase_N.json` - Post-phase violations
- `qa/phase_N_log.txt` - Execution log for phase
- `reports/phase_N_summary.md` - Phase completion report

**Phase 6 artifacts**:
- `artifacts/audit_final.json` - Zero violations
- `artifacts/remediation_manifest.json` - All fixes summary
- `reports/completion_summary.md` - Final report
- `COMPLETION_REPORT.md` - Task deliverable

### Storage & Lifecycle

```
tasks/AV-001-authenticity-remediation/
├── context/
│   ├── hypothesis.md
│   ├── design.md (this file)
│   ├── evidence.json
│   ├── data_sources.json
│   ├── adr.md
│   ├── assumptions.md
│   └── cp_paths.json
├── artifacts/
│   ├── audit_before_phase1.json
│   ├── audit_after_phase1.json
│   ├── ... (one set per phase)
│   └── audit_final.json
├── qa/
│   ├── phase_1_log.txt
│   ├── phase_2_log.txt
│   └── ... (one per phase)
├── reports/
│   ├── phase_1_summary.md
│   ├── phase_2_summary.md
│   └── ... (one per phase)
├── EXECUTIVE_SUMMARY.md
├── QUICK_START_CHECKLIST.md
├── REMEDIATION_PLAN.md
├── ISSUE_TRACKER.md
├── TROUBLESHOOTING_GUIDE.md
└── README.md
```

---

## Success Validation

### Checkpoints (Phase Completion)

After each phase, verify:

1. **Violation count reduced**: `audit_after_phase_N.json` shows fewer violations
2. **No regressions**: Full test suite passes (523 tests)
3. **Type safety maintained**: `mypy --strict` = 0 errors
4. **Phase artifacts created**: `artifacts/audit_after_phase_N.json` exists
5. **Commit message tagged**: All fixes include phase issue ID

### Final Validation (Phase 6)

Before declaring complete:

```bash
# Run full audit
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json
# ✅ Expect: 0 violations, all gates PASS

# Verify determinism (3x runs)
bash /tmp/test_det.sh
# ✅ Expect: Byte-identical outputs

# Run full test suite
pytest tests/ --cov=agents,apps,libs --cov-report=term
# ✅ Expect: 523/523 pass, ≥95% coverage

# Type check
mypy --strict apps/ agents/ libs/
# ✅ Expect: 0 errors

# Docker offline test
docker run --network none esg-scorer /trace
# ✅ Expect: 200 OK, no network calls
```

---

## Sign-Off

**Design reviewed by**: SCA Protocol specifications
**Verification strategy approved**: User authorization
**Success criteria locked**: At plan phase
**Contingency plan**: Rollback to audit-baseline-20251026

---

**Document**: AV-001 Design & Verification
**Version**: 1.0
**Created**: 2025-10-26
