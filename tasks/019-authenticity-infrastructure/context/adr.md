# Architecture Decision Records (ADR) — Task 019

**Task**: 019-authenticity-infrastructure
**Status**: Context Phase
**Last Updated**: 2025-10-26

---

## ADR-019-001: Dependency Injection vs Global Monkey-Patching

**Date**: 2025-10-26
**Status**: Accepted
**Context**:

Task 019 requires replacing nondeterministic time operations (`datetime.now()`, `time.time()`) with a deterministic Clock abstraction. Two approaches considered:

1. **Global Monkey-Patching**: Replace `datetime.now` globally at module import
   - Example: `datetime.datetime.now = lambda: datetime.fromtimestamp(FIXED_TIME)`
   - Pros: No code changes required
   - Cons: Fragile, breaks on direct imports (`from datetime import datetime`), order-dependent, hard to debug

2. **Dependency Injection**: Provide Clock via `get_clock()` / `set_clock()` service locator
   - Example: `timestamp = get_clock().now()`
   - Pros: Explicit, testable, IDE-friendly, type-safe
   - Cons: Requires code changes at all call sites

**Decision**:

Use **Dependency Injection** with service locator pattern (`get_clock()`, `set_clock()`).

**Rationale**:
- Explicit is better than implicit (Zen of Python)
- Type hints work correctly with injected dependencies
- Test-time overrides are isolated (no global state pollution)
- Aligns with SCA protocol emphasis on transparency and testability
- Supports differential testing (compare FIXED_TIME vs real clock)

**Consequences**:
- Requires updating 81 call sites (one-time effort)
- Clear code intent: `get_clock().now()` signals "this is an injectable dependency"
- Future phases can use same pattern for other abstractions (RNG, HTTP)

**Alternatives Rejected**:
- Monkey-patching: Too fragile for production code
- No abstraction: Violates SCA determinism requirements

---

## ADR-019-002: JSON Exemption Registry Format

**Date**: 2025-10-26
**Status**: Accepted
**Context**:

Some violations are intentional (e.g., `to_json()` in test files for human-readable fixtures, `eval/exec` in audit detector meta-code). Need a way to document and enforce approved exemptions without silencing the audit tool.

Options:
1. **Inline Comments**: `# @sca-exempt: json_as_parquet: test fixture`
2. **JSON Registry**: `.sca/exemptions.json` with structured records
3. **YAML Configuration**: `.sca/exemptions.yaml`

**Decision**:

Use **JSON Registry** at `.sca/exemptions.json` with the following schema:

```json
{
  "exemptions": [
    {
      "file": "tests/scoring/test_rubric_models.py",
      "line": 385,
      "violation_type": "json_as_parquet",
      "justification": "Test file: to_json() used for human-readable test fixtures (not data artifacts)",
      "approved_by": "tech-lead",
      "approved_date": "2025-10-26",
      "expires": "2026-06-01",
      "review_notes": "Re-evaluate if test fixtures grow beyond 10 files"
    }
  ]
}
```

**Rationale**:
- **JSON**: Machine-readable, supports validation via JSON Schema, widely supported
- **Structured**: Explicit file/line/type mapping for audit tool parsing
- **Auditable**: approved_by, approved_date, expires fields for governance
- **Centralized**: Single source of truth in `.sca/` directory (version-controlled)

**Consequences**:
- Audit tool (`scripts/qa/authenticity_audit.py`) updated to check exemptions before reporting violations
- Expired exemptions automatically fail (force re-review)
- Exemption changes trigger git diff review (visibility)

**Alternatives Rejected**:
- Inline comments: Not machine-readable, scattered across codebase
- YAML: JSON simpler, better Python stdlib support (no external dependency)

---

## ADR-019-003: Gradual Rollout Strategy (Top 20 First)

**Date**: 2025-10-26
**Status**: Accepted
**Context**:

81 files have `datetime.now()` / `time.time()` violations. Two rollout strategies:

1. **Big Bang**: Update all 81 files in one commit
   - Pros: Faster completion
   - Cons: High regression risk, hard to debug failures, difficult rollback

2. **Gradual Rollout**: Update top 20 high-impact files first, then remainder
   - Pros: Lower risk, easier debugging, incremental validation
   - Cons: Longer timeline, potential for inconsistent state mid-rollout

**Decision**:

Use **Gradual Rollout** with prioritization:

**Phase 2a (Week 1, Days 2-3)**: Top 20 high-impact files
- Data providers: `agents/crawler/data_providers/*.py` (7 files)
- Storage layer: `libs/storage/astradb_*.py` (2 files)
- Pipeline orchestration: `apps/pipeline_orchestrator.py` (1 file)
- *Impact*: Crawlers and storage are foundation of ESG data pipeline

**Phase 2b (Week 1, Days 4-5)**: Remaining 61 files
- Scripts: `scripts/*.py` (10 files)
- Evaluation: `apps/evaluation/*.py` (2 files)
- Ingestion: `apps/ingestion/*.py` (3 files)
- Tests: `tests/infrastructure/*.py` (3 files)
- *Impact*: Less critical, can tolerate regressions

**Rationale**:
- **Risk Mitigation**: High-impact files tested first (fail-fast principle)
- **Incremental Validation**: Run test suite after Phase 2a (catch issues early)
- **Rollback Boundary**: Can rollback Phase 2a independently if needed
- **Team Velocity**: Early wins build confidence for remainder

**Consequences**:
- Some files use `get_clock()`, others still use `datetime.now()` during Phase 2a
- Must document "mixed state" in PR description (temporary)
- Final validation ensures all 81 files remediated before Phase 2 complete

**Alternatives Rejected**:
- Big bang: Too risky for 81-file change
- Random order: Misses opportunity to validate high-impact components first

---

## ADR-019-004: HTTPClient Interface Design

**Date**: 2025-10-26
**Status**: Accepted
**Context**:

Need HTTP abstraction for 33 network violations. Two interface designs:

1. **Minimal Interface**: Only `get()` and `post()` methods
2. **Full requests API**: Mirror entire `requests.Session` interface

**Decision**:

Use **Minimal Interface** (`get`, `post` only) with future extensibility:

```python
class HTTPClient(ABC):
    @abstractmethod
    def get(self, url: str, **kwargs) -> Any:
        pass

    @abstractmethod
    def post(self, url: str, **kwargs) -> Any:
        pass
```

**Rationale**:
- **YAGNI Principle**: Codebase only uses GET/POST, not PUT/DELETE/PATCH
- **Simpler Mocking**: MockHTTPClient only needs 2 methods
- **Extensibility**: Can add methods later if needed (backward-compatible)
- **Type Safety**: `-> Any` allows both `requests.Response` (real) and dict (mock)

**Consequences**:
- If future code needs PUT/DELETE, add to interface (one-time breaking change)
- Fixtures must handle both GET and POST patterns (but both use same logic)

**Alternatives Rejected**:
- Full requests API: Overengineering (99% of code uses GET only)
- Single `request(method, url, **kwargs)`: Less explicit, worse type hints

---

## ADR-019-005: Test Fixture Generation Strategy

**Date**: 2025-10-26
**Status**: Accepted
**Context**:

MockHTTPClient requires fixtures for 33 files using network calls. Two generation strategies:

1. **Manual Fixtures**: Hand-write JSON responses
2. **Captured Fixtures**: Run code once with RealHTTPClient, save responses

**Decision**:

Use **Captured Fixtures** (one-time capture, version-controlled):

**Process**:
1. Create `scripts/capture_http_fixtures.py`
2. Run with `RealHTTPClient` against live APIs (one-time)
3. Save responses to `fixtures/http_responses/<provider>_response.json`
4. Version-control fixtures (git)
5. Tests use `MockHTTPClient` with captured fixtures

**Rationale**:
- **Accuracy**: Real API responses (not synthetic)
- **Completeness**: Captures all fields (headers, status, body)
- **Maintainability**: Re-capture if API changes (simple re-run)
- **Performance**: Fixtures load from disk (fast, no network)

**Consequences**:
- Initial setup requires live API access (one-time)
- Fixtures may become stale if APIs change (re-capture needed)
- Fixtures are binary data (not human-editable), but JSON format aids debugging

**Alternatives Rejected**:
- Manual fixtures: Error-prone, incomplete, high maintenance burden
- Live APIs in tests: Non-deterministic, requires network, slow

---

**End of adr.md**
