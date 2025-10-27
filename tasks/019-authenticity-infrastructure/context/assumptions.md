# Assumptions — Task 019: Authenticity Infrastructure

**Task**: 019-authenticity-infrastructure
**Status**: Context Phase
**Last Updated**: 2025-10-26

---

## Technical Assumptions

### 1. Existing Tests Do Not Rely on Wall-Clock Time

**Assumption**: Current test suite does not assert specific wall-clock timestamps (e.g., "assert datetime.now().year == 2025")

**Validation**: Manual review of test files + grep search for `datetime.now()` in assertions

**Risk**: MEDIUM — If tests assert current year/month, will fail with FIXED_TIME

**Mitigation**:
- Phase 2 includes test suite run with FIXED_TIME=1609459200 (2021-01-01)
- Any failing tests updated to assert date ranges or use injected clock
- If >10 tests fail, re-evaluate FIXED_TIME value or add per-test overrides

**Contingency**: If assumption invalid, create per-module fixtures with appropriate FIXED_TIME values

---

### 2. Production Deployments Can Set FIXED_TIME Environment Variable

**Assumption**: Production infrastructure (Docker, Kubernetes, bare metal) supports setting `FIXED_TIME` env var for deterministic testing

**Validation**: Check deployment scripts, Dockerfiles, CI/CD pipelines

**Risk**: LOW — Environment variables universally supported

**Mitigation**:
- Document FIXED_TIME usage in `REPRODUCIBILITY.md`
- Add to `.env.example`: `FIXED_TIME=0  # Set to Unix timestamp for deterministic testing`
- CI/CD pipeline sets FIXED_TIME for reproducibility tests

**Contingency**: If FIXED_TIME not available, Clock defaults to real-time (production behavior unchanged)

---

### 3. HTTP Fixtures Can Be Generated from Live API Responses

**Assumption**: Can execute one-time live API calls to CDP, GRI, SASB, SEC EDGAR to capture responses as fixtures

**Validation**: Test API endpoints with curl/requests, verify responses contain expected data

**Risk**: MEDIUM — APIs may require authentication, rate-limiting, or terms-of-service compliance

**Mitigation**:
- Use public/test endpoints where available
- Respect rate limits (1 request per 5 seconds)
- Cache responses immediately (one-time capture)
- If authentication required, use environment variable for API keys (not committed)

**Contingency**: If live APIs unavailable, use synthetic fixtures based on API documentation (lower fidelity)

---

### 4. Existing Code Can Tolerate Clock/HTTP Injection

**Assumption**: Production code can accept injected Clock/HTTPClient without major refactoring

**Validation**: Code review of data providers, pipeline orchestrators, storage adapters

**Risk**: LOW — Most code uses procedural style (easy to inject via function params)

**Mitigation**:
- ADR-019-001 specifies service locator pattern (`get_clock()`) for minimal invasiveness
- HTTPClient injected via constructor params (default to RealHTTPClient)
- Gradual rollout (Phase 2a: top 20 files) validates pattern before full rollout

**Contingency**: If injection infeasible for specific module, document exemption and use monkey-patching for that module only

---

### 5. SEED Environment Variable Universally Respected

**Assumption**: All randomness in codebase can be seeded via SEED env var (or PYTHONHASHSEED)

**Validation**: Grep search for `random.`, `np.random`, `torch.manual_seed`

**Risk**: LOW — Only 1 FATAL violation (unseeded random.randint)

**Mitigation**:
- Phase 1 fixes unseeded random
- Add `libs/utils/determinism.py` with `get_seeded_random()` factory
- Document usage in `REPRODUCIBILITY.md`

**Contingency**: If external libraries use unseeded random, document as exemption and note in validation report

---

### 6. Test Suite Tolerates Zero Network Access

**Assumption**: Disabling network (`pytest-socket`) will not break tests after Phase 3 remediation

**Validation**: Run `pytest --disable-socket` after Phase 3 complete

**Risk**: MEDIUM — Some integration tests may still attempt live network calls

**Mitigation**:
- Mark integration tests requiring network with `@pytest.mark.requires_network`
- CI/CD runs regular tests with `--disable-socket`, integration tests separately
- Document network-required tests in test suite README

**Contingency**: If critical tests require network, add to exemptions and document rationale

---

### 7. Exemption Registry Covers All Intentional Violations

**Assumption**: 5 exemptions (test fixtures, audit meta-code) are complete and no additional exemptions needed

**Validation**: Post-remediation audit should show exactly 5 WARN violations (all documented)

**Risk**: LOW — Audit report is deterministic and comprehensive

**Mitigation**:
- `.sca/exemptions.json` created in Phase 1
- Any new exemptions added with expiry dates and justification
- Monthly review of exemptions (check expiry dates)

**Contingency**: If additional exemptions needed, follow ADR-019-002 format (file, line, type, justification, expiry)

---

### 8. 3-Week Sprint Timeline Is Achievable

**Assumption**: 43 hours of effort can be completed in 3-week sprint (15 work days)

**Validation**: ~3 hours per day average (realistic for single-focus task)

**Risk**: MEDIUM — Unforeseen blockers (test failures, API issues) may extend timeline

**Mitigation**:
- Phase-by-phase gates allow early detection of delays
- If Phase 2 exceeds 16 hours, re-estimate remaining phases
- Buffer time in Week 3 (Days 18-21) for final validation and fixes

**Contingency**: If timeline slips, prioritize Phases 1-4 (critical) over Phases 5-6 (nice-to-have)

---

### 9. Task 018 Coverage Gap Is Isolated to 2-3 Missing Branches

**Assumption**: Task 018's 0.6% coverage gap (94.4% → 95%) represents ~2-3 uncovered conditionals

**Validation**: Run `pytest --cov-report=term-missing` on Task 018 CP files

**Risk**: LOW — Coverage reports are deterministic

**Mitigation**:
- Phase 6 starts with coverage report analysis (1 hour)
- If >5 missing branches, increase Phase 6 effort estimate
- Add targeted tests for missing branches only (avoid over-testing)

**Contingency**: If coverage gap exceeds 5 missing branches, escalate to Task 018 owner for guidance

---

### 10. No PII in Violation Data or Audit Reports

**Assumption**: Authenticity audit report contains file paths, line numbers, code snippets—no personal identifiable information

**Validation**: Manual review of `artifacts/authenticity/report.json`

**Risk**: NEGLIGIBLE — Audit scans code, not user data

**Mitigation**:
- `data_sources.json` marks all sources as `pii_flag: false`
- If code snippets contain hardcoded credentials (accidentally), redact in exemptions.json

**Contingency**: If PII found, redact from audit report and regenerate with `--redact-pii` flag (to be implemented if needed)

---

## Dependency Assumptions

### Upstream Dependencies (Must Be Complete)

1. ✅ **Authenticity Audit (AV-001)**: COMPLETE (2025-10-26)
   - Audit report generated and validated
   - 149 violations identified with file/line mappings

2. ✅ **AUTHENTICITY_REMEDIATION_PLAN.md**: COMPLETE (2025-10-26)
   - Phase-by-phase strategy documented
   - Effort estimates and acceptance criteria defined

### Downstream Dependencies (Blocked Until Task 019 Complete)

1. **Task 020+**: All future tasks benefit from determinism infrastructure
   - Assumption: No future task introduces new time/RNG violations (enforced by CI)
   - Risk: LOW — CI validation gate prevents regressions

2. **Production Deployment**: Requires FIXED_TIME capability
   - Assumption: Ops team can set FIXED_TIME in staging for reproducibility tests
   - Risk: LOW — Standard env var, widely supported

---

## Environmental Assumptions

### 1. Python 3.11+ Environment

**Assumption**: Task 019 runs on Python 3.11.9 (current project venv)

**Risk**: NEGLIGIBLE — Version-controlled in `.python-version`

**Validation**: `python --version` in CI/CD pipeline

---

### 2. Windows Development, Linux Production

**Assumption**: Code developed on Windows (current session), deployed on Linux

**Risk**: LOW — Python abstracts OS differences

**Mitigation**: Use `pathlib.Path` for file paths (cross-platform)

**Validation**: Run test suite on both Windows and Linux in CI/CD

---

### 3. No External Service Dependencies for Core Functionality

**Assumption**: libs/utils/* modules do not depend on external services (Redis, databases, APIs)

**Risk**: NEGLIGIBLE — Infrastructure utilities are self-contained

**Validation**: No network calls in `libs/utils/clock.py`, `determinism.py`

---

## Constraints

### 1. No Breaking Changes to Public APIs

**Constraint**: Infrastructure changes must be backward-compatible with existing code

**Enforcement**: Existing code continues to work with default `RealHTTPClient()` and real clock

**Trade-off**: Requires gradual rollout (cannot force all code to use new APIs immediately)

---

### 2. No External Dependencies for Infrastructure Modules

**Constraint**: libs/utils/* must use Python stdlib only (no requests, numpy, pandas)

**Rationale**: Avoid circular dependencies (requests is what we're abstracting!)

**Validation**: `pipdeptree --packages libs` shows only stdlib imports

---

### 3. Zero Tolerance for Placeholders in CP Modules

**Constraint**: Infrastructure modules (clock.py, determinism.py, http_client.py) cannot contain `TODO`, `FIXME`, or hardcoded stubs

**Enforcement**: Placeholder detection in validation gate (blocks if found)

**Trade-off**: Must implement full functionality in Phase 1 (cannot defer)

---

**End of assumptions.md**
