# Assumptions - Phase 2

**Task ID**: 011-multi-source-phase2
**SCA Version**: v13.8-MEA
**Date**: 2025-10-24

---

## Technical Assumptions

### A1: Python's `sorted()` is Deterministic

**Assumption**: For same input list, `sorted(lst, key=lambda x: ...)` always returns same output.

**Evidence**: Python documentation guarantees stable sort (Timsort algorithm).

**Impact if Wrong**: Prioritization would be non-deterministic, breaking reproducibility.

**Mitigation**: Property-based tests verify determinism explicitly.

**Status**: ✅ Verified in Python docs (https://docs.python.org/3/library/functions.html#sorted)

---

### A2: Tier System is Stable (1=Best, 2=Medium, 3=Lowest)

**Assumption**: Tier numbering convention (1=highest quality, 3=lowest quality) won't change during project lifetime.

**Evidence**: Aligned with v3 data_ingestion_plan.md.

**Impact if Wrong**: All prioritization logic would need to be reversed.

**Mitigation**: Document tier convention in `SourceRef` docstring. If convention changes, update `_prioritize_candidates()` key function.

**Status**: ✅ Documented in design.md and ADR-002

---

### A3: Priority Score Range is 0-100 (Lower = Better)

**Assumption**: All providers assign priority_score in range [0, 100] where 0 = highest priority, 100 = lowest.

**Evidence**: Pydantic validator enforces range. Aligned with v3 spec.

**Impact if Wrong**: Providers could assign invalid scores, breaking prioritization.

**Mitigation**: Pydantic `@validator` raises `ValidationError` for out-of-range scores.

**Status**: ✅ Enforced by Pydantic validation

---

### A4: Phase 1 SEC EDGAR Provider is Backward Compatible

**Assumption**: Phase 1 provider can be updated to return `List[SourceRef]` without breaking existing functionality.

**Evidence**: Differential tests verify compatibility.

**Impact if Wrong**: Would need to maintain two versions of SEC EDGAR provider (breaking change).

**Mitigation**: Differential tests (`test_phase1_provider_compatible_with_phase2_crawler`) ensure no regression.

**Status**: ⏸️ To be verified in implementation phase

---

### A5: Number of Candidates is Manageable (n < 1000)

**Assumption**: For any company + year, total candidates across all tiers is < 1000.

**Evidence**: Typical company has ~5-10 reports per year across all sources.

**Impact if Wrong**: O(n log n) sorting could become bottleneck.

**Mitigation**: If n > 1000 becomes common, optimize with heap-based selection (top-k candidates only).

**Status**: ✅ Reasonable assumption for ESG reports

---

### A6: Provider Search Failures are Non-Fatal

**Assumption**: If one provider's `search()` fails, other providers can still succeed.

**Evidence**: Fail-open design in `search_company_reports()` (try-except continues on exception).

**Impact if Wrong**: Single provider failure would crash entire search.

**Mitigation**: Wrap each `provider.search()` in try-except, log warning, continue.

**Status**: ✅ Implemented in design.md

---

### A7: Download Failures Require Fallback to Next Candidate

**Assumption**: Best candidate (by priority) may fail to download (404, timeout, rate limit). Must try next candidate.

**Evidence**: Real-world network failures, rate limits, transient errors.

**Impact if Wrong**: Would fail on first download error instead of falling back.

**Mitigation**: `download_best_report()` loops through all candidates until one succeeds.

**Status**: ✅ Implemented in design.md

---

### A8: SourceRef is Immutable (Frozen Pydantic Model)

**Assumption**: SourceRef objects should not be modified after creation (prevents bugs from accidental mutation).

**Evidence**: Pydantic Config.frozen=True makes model immutable.

**Impact if Wrong**: Code could mutate SourceRef (e.g., change tier after creation), breaking prioritization.

**Mitigation**: Pydantic enforces immutability at runtime (raises exception on mutation attempt).

**Status**: ✅ Enforced by Pydantic Config.frozen=True

---

### A9: Mock Providers are Sufficient for Phase 2 Validation

**Assumption**: Can validate multi-source orchestration logic using mock providers (no real web scraping needed).

**Evidence**: Unit tests with mocked providers can verify search, prioritize, download logic.

**Impact if Wrong**: Real web scrapers might behave differently than mocks (e.g., async I/O, complex error handling).

**Mitigation**: Phase 2b will replace mocks with real implementations. Integration tests will catch discrepancies.

**Status**: ✅ Documented in ADR-007 (mocks for Phase 2, real scrapers in Phase 2b)

---

### A10: Pydantic Validation Overhead is Negligible

**Assumption**: SourceRef validation (range checks, type checks) takes microseconds, not milliseconds.

**Evidence**: Pydantic v2 uses Rust core (pydantic-core), very fast.

**Impact if Wrong**: Validation could be bottleneck for large candidate lists.

**Mitigation**: If overhead becomes measurable, can disable validation in production (use `model_construct()` for perf-critical paths).

**Status**: ✅ Pydantic v2 is highly optimized

---

## Testing Assumptions

### A11: Hypothesis Can Generate All Edge Cases

**Assumption**: Hypothesis library can generate edge cases we don't think of manually (empty lists, ties, extreme values).

**Evidence**: Hypothesis docs show examples of finding bugs in production code.

**Impact if Wrong**: Manual tests might miss edge cases (e.g., all candidates same tier and priority_score).

**Mitigation**: Use broad strategies (`st.lists`, `st.integers`, `st.builds`) to maximize input diversity.

**Status**: ✅ Hypothesis is well-proven in Python ecosystem

---

### A12: TDD Approach Reduces Debugging Time

**Assumption**: Writing tests before implementation catches bugs earlier, reducing total development time.

**Evidence**: SCA v13.8 protocol mandates TDD-first. Phase 1 achieved 87% coverage with TDD.

**Impact if Wrong**: Could waste time writing tests for incorrect design.

**Mitigation**: Context gate (hypothesis.md, design.md) ensures design is validated before coding.

**Status**: ✅ SCA protocol requirement

---

### A13: ≥95% Coverage is Achievable Without Defensive Code

**Assumption**: Can reach ≥95% coverage by testing real use cases (not adding artificial code just to increase coverage).

**Evidence**: Phase 1 achieved 87% without artificial tests. Remaining 13% is defensive error handling.

**Impact if Wrong**: Might need to add tests for unreachable code (e.g., impossible error conditions).

**Mitigation**: Focus on realistic failure paths (network timeout, invalid response, empty candidate list).

**Status**: ⏸️ To be verified in implementation phase

---

### A14: Mock Responses Match Real API Behavior

**Assumption**: Mocked provider responses (using `responses` library) are representative of real API responses.

**Evidence**: Phase 1 integration tests verify real SEC EDGAR API behavior.

**Impact if Wrong**: Unit tests might pass, but integration tests fail (schema mismatch, unexpected fields).

**Mitigation**: Integration tests with real SEC EDGAR API (Phase 1 provider). E2E tests with real multi-source download (Phase 2b).

**Status**: ✅ Integration tests planned

---

### A15: Failure-Path Tests Cover All Exception Types

**Assumption**: 6 failure-path tests are sufficient to cover all error conditions (DocumentNotFoundError, RateLimitExceededError, etc.).

**Evidence**: Phase 1 achieved 100% coverage on exceptions.py with 6 failure-path tests.

**Impact if Wrong**: Uncaught exception types could crash application in production.

**Mitigation**: Enumerate all exception types in design.md, write one test per exception.

**Status**: ✅ Exception types documented in Phase 1

---

## Data Assumptions

### A16: No PII in Test Fixtures

**Assumption**: Mock provider responses and Hypothesis-generated data contain no personally identifiable information.

**Evidence**: All test data is synthetic (hand-crafted or randomly generated).

**Impact if Wrong**: Could leak PII in version control, violate privacy regulations.

**Mitigation**: Manual review of all test fixtures. No production data used in tests.

**Status**: ✅ Documented in data_sources.json

---

### A17: SEC EDGAR API is Stable (No Breaking Changes During Phase 2)

**Assumption**: SEC EDGAR API schema (submissions endpoint, filings structure) won't change during Phase 2 implementation (2-3 days).

**Evidence**: SEC EDGAR API has been stable for years.

**Impact if Wrong**: Phase 1 provider could break, failing integration tests.

**Mitigation**: Integration tests marked `@pytest.mark.integration` (can skip if API is down). Error handling for API schema changes.

**Status**: ✅ Low risk (SEC API is stable)

---

### A18: Coverage Artifacts are Deterministic

**Assumption**: For same code and tests, `pytest-cov` generates identical coverage.xml.

**Evidence**: Coverage is based on executed code paths (deterministic given same inputs).

**Impact if Wrong**: Coverage could fluctuate between runs, making gate unreliable.

**Mitigation**: Use mocked providers (no real network I/O) in unit tests. Integration tests may have variance (mark with `@pytest.mark.integration`).

**Status**: ✅ Coverage is deterministic for unit tests

---

### A19: Git Timestamps Accurately Reflect Commit Order

**Assumption**: `git log --all --pretty=format:"%H %s" -- <file>` returns commits in chronological order (oldest to newest).

**Evidence**: Git log is sorted by commit timestamp by default.

**Impact if Wrong**: TDD Guard could incorrectly flag tests as "created after code".

**Mitigation**: Use `git log --reverse` to show oldest commits first. Manually verify first commit is test file.

**Status**: ✅ Git log order is reliable

---

### A20: Phase 2 Completes in 2-3 Days (18-20 Hours)

**Assumption**: Context gate (7 files) + TDD tests (24 tests) + implementation + validation can be completed in 2-3 days.

**Evidence**: Phase 1 completed in similar timeline (context + tests + implementation + validation).

**Impact if Wrong**: Could delay Phase 3/4 timeline, blocking v3 completion.

**Mitigation**: Break Phase 2 into Phase 2a (orchestration logic, 2-3 days) and Phase 2b (real web scrapers, 3-5 days). Phase 2a is minimum viable.

**Status**: ✅ Timeline documented in hypothesis.md, conservative estimate

---

**Document Prepared By**: Scientific Coding Agent v13.8-MEA
**Review Status**: Ready for implementation
**Total Assumptions**: 20 (10 technical, 5 testing, 5 data)
**Risk Level**: Low (all assumptions backed by evidence or mitigation plans)
