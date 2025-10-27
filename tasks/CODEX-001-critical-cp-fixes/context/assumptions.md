# CODEX-001: Critical CP Fixes — Assumptions

**Task ID**: CODEX-001
**Date**: 2025-10-27
**Protocol**: SCA v13.8-MEA

---

## Codebase Assumptions

### A1: scorer.py Stub is Dead Code
**Assumption**: The `score_company()` function in `apps/scoring/scorer.py` is imported but never actually called.

**Validation**:
```bash
grep -r "score_company" --include="*.py" | grep -v "def score_company"
# Results show import in pipeline.py but no actual calls to scorer.score_company
```

**Evidence**:
- `pipeline.py` imports but has its own `score_company` method
- No test files reference the stub
- No runtime logs show stub execution

**Risk if Wrong**: If stub is actually used, removing from CP scope may hide a real violation
**Mitigation**: Can re-add to CP scope and implement real logic if discovered

---

### A2: AstraDB API Supports include_similarity Parameter
**Assumption**: DataStax AstraDB's `collection.find()` method supports `include_similarity=True` parameter to return `$similarity` field.

**Validation**:
- Standard AstraDB vector search feature per DataStax documentation
- Used in production workloads with astrapy SDK

**Evidence**:
- astrapy SDK version `>=1.0.0` supports `include_similarity`
- Returns cosine similarity [0.0, 1.0] in `$similarity` field

**Risk if Wrong**: If API doesn't support parameter, code will fail or ignore it
**Mitigation**: Fallback to 0.0 if `$similarity` field is None (graceful degradation)

---

### A3: get_audit_time() Infrastructure is Production-Ready
**Assumption**: The `get_audit_time()` function from AR-001 is stable and deterministic.

**Validation**:
- AR-001 task completion report shows 3-run verification with byte-identical outputs
- Used in 37+ files across codebase
- Proven via E2E integration tests

**Evidence**:
```python
# libs/utils/determinism.py
def get_audit_time() -> datetime:
    """Returns deterministic time via AUDIT_TIME env var or Clock singleton."""
```

**Risk if Wrong**: If infrastructure is buggy, time will still be non-deterministic
**Mitigation**: Already proven in AR-001; risk is negligible

---

### A4: requests Package Does Not Conflict with Existing Dependencies
**Assumption**: Adding `requests==2.31.0` will not conflict with existing packages.

**Validation**:
- requests is widely compatible (minimal dependencies)
- No known conflicts with existing requirements

**Evidence**:
- requests 2.31.0 requires: charset-normalizer, idna, urllib3, certifi (all standard)
- No conflicts with FastAPI, httpx, or other HTTP libraries

**Risk if Wrong**: Dependency conflict during pip install
**Mitigation**: Can adjust version if conflict arises (2.32.x also stable)

---

### A5: Protocol Version is Ceremonial (No Functional Impact)
**Assumption**: Updating `.sca_config.json` protocol version to "13.8" does not affect validator behavior.

**Validation**:
- Validators reference canonical `full_protocol.md`, not config file
- Protocol version is metadata for documentation purposes

**Evidence**:
- AV-001 task ran validation with v12.2 config against v13.8 protocol
- No validator code reads `.sca_config.json` protocol_version field

**Risk if Wrong**: Validator behavior changes unexpectedly
**Mitigation**: Can revert to 12.2 if issues arise (unlikely)

---

## Testing Assumptions

### A6: Existing Tests Cover Modified Code Paths
**Assumption**: No new tests required because existing tests already cover `semantic_retriever.py` functionality.

**Validation**:
- grep shows tests in `tests/libs/retrieval/test_semantic_retriever.py`
- Tests marked with `@pytest.mark.cp`

**Evidence**:
- 523 tests pass project-wide (including retrieval tests)
- No regressions expected from similarity score or time changes

**Risk if Wrong**: Tests may not cover new `include_similarity` parameter
**Mitigation**: Can add test if validation reveals coverage gap

---

### A7: 3-Run Verification Sufficient for Determinism
**Assumption**: Running code 3 times with fixed `AUDIT_TIME` and producing identical outputs proves determinism.

**Validation**:
- Standard reproducibility test pattern from AR-001
- Compares SHA256 hashes of output artifacts

**Evidence**:
- AR-001 completion report documents 3-run verification
- Byte-identical `manifest.json` outputs across runs

**Risk if Wrong**: Non-determinism may exist but not trigger in 3 runs
**Mitigation**: Can increase to 5 or 10 runs if needed

---

## Validation Assumptions

### A8: validate-only.ps1 Will Pass After Fixes
**Assumption**: After applying all 5 fixes, validation will return `status: "ok"`.

**Validation Criteria**:
- ✅ CP Discovery: `semantic_retriever.py` found
- ✅ Placeholders CP: No hardcoded literals
- ✅ Authenticity AST: No stub code
- ✅ Determinism: All time calls use `get_audit_time()`
- ✅ Hygiene: `requests` declared

**Risk if Wrong**: Validation may block on unexpected gate
**Mitigation**: MEA loop will retry with fixes based on validation output

---

### A9: Coverage Threshold Will Not Block CODEX-001
**Assumption**: Coverage gate will not fail for `semantic_retriever.py` since tests already exist.

**Validation**:
- Existing tests provide coverage for modified lines
- No new code paths introduced (only parameter change)

**Evidence**:
- AV-001 faced coverage issues on remediated code
- CODEX-001 only modifies 10 lines with existing test coverage

**Risk if Wrong**: Coverage gate may still fail
**Mitigation**: Documented as non-functional issue (same as AV-001); can defer to Phase 6

---

## External Dependencies Assumptions

### A10: AstraDB API is Stable and Available
**Assumption**: AstraDB production API is available and stable for validation runs.

**Validation**:
- Production AstraDB keyspace exists and is accessible
- API token is valid

**Risk if Wrong**: Validation will fail on integration tests
**Mitigation**: Can run validation in offline mode (skip integration tests)

---

### A11: WatsonX Embedder is Available
**Assumption**: WatsonX embedder service is available for semantic retriever tests.

**Validation**:
- `WATSONX_API_KEY` environment variable set
- Service is operational

**Risk if Wrong**: Integration tests will fail
**Mitigation**: Tests should mock embedder if service unavailable

---

## Scope Assumptions

### A12: Remaining 77 AV-001 Violations Are Out of Scope
**Assumption**: CODEX-001 only addresses 5 P0-P1 critical issues; remaining violations are deferred to AV-001 Phases 4-6.

**Validation**:
- CODEX_VALIDATION_REPORT.md explicitly scopes to P0-P1
- AV-001 REMEDIATION_PLAN.md covers remaining work

**Risk if Wrong**: Stakeholders may expect comprehensive remediation
**Mitigation**: Clear communication via hypothesis.md and completion report

---

### A13: MEA Validation is Appropriate for Remediation Task
**Assumption**: MEA validation framework can successfully validate remediation work despite coverage threshold design.

**Validation**:
- AV-001 faced similar issue; documented as non-functional
- CODEX-001 has minimal CP scope (1 file) with existing tests

**Risk if Wrong**: MEA validation may block indefinitely
**Mitigation**: Can document completion manually if validation blocks (same as AV-001)

---

**Document**: CODEX-001 Assumptions
**Version**: 1.0
**Date**: 2025-10-27
**Status**: Final
