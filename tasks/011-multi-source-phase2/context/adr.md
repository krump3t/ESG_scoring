# Architecture Decision Records (ADR) - Phase 2

**Task ID**: 011-multi-source-phase2
**SCA Version**: v13.8-MEA
**Date**: 2025-10-24

---

## ADR-001: Use Python's Built-in `sorted()` for Prioritization

**Status**: Accepted

**Context**:
Need to sort candidates by `(tier, priority_score)` with deterministic, stable ordering.

**Decision**:
Use Python's built-in `sorted(candidates, key=lambda c: (c.tier, c.priority_score))`.

**Alternatives Considered**:
1. **Custom sorting algorithm** (e.g., insertion sort)
   - ❌ Reinvents wheel, higher complexity (CCN), harder to test
2. **Pandas DataFrame sorting** (`df.sort_values(['tier', 'priority_score'])`)
   - ❌ Adds dependency, overkill for simple list sorting
3. **SQL ORDER BY** (store candidates in DuckDB, query with ORDER BY)
   - ❌ Over-engineered for in-memory sorting, adds I/O overhead

**Rationale**:
- ✅ Python's Timsort is stable (preserves order of equal elements)
- ✅ O(n log n) complexity (acceptable for n < 1000 candidates)
- ✅ Deterministic (same input → same output)
- ✅ Simple implementation (CCN = 1, easy to test with property-based tests)
- ✅ No external dependencies

**Consequences**:
- ✅ Prioritization logic is single line of code (simple, maintainable)
- ✅ Property-based tests can verify invariants (tier ordering) for ALL valid inputs
- ⚠️ Performance degrades to O(n log n) for very large n (acceptable trade-off)

---

## ADR-002: Search ALL Tiers Before Prioritization (Not Sequential Fallback)

**Status**: Accepted

**Context**:
v3 enhancement #1 requires comprehensive search across all tiers, then prioritized download. This differs from Phase 1's single-source approach and from sequential fallback (try Tier 1, if fail → try Tier 2, etc.).

**Decision**:
Implement `search_company_reports()` that:
1. Calls `search()` on ALL enabled providers across ALL tiers
2. Returns flat `List[SourceRef]` (complete candidate list)
3. Prioritization happens AFTER search (separate method)

**Alternatives Considered**:
1. **Sequential fallback** (try Tier 1, if fail → Tier 2, ...)
   - ❌ Blocks high-value Tier 3 PDF with low-value Tier 1 HTML
   - ❌ Doesn't give user best available report
2. **Parallel search with early termination** (stop after first tier returns candidates)
   - ❌ Same problem as sequential fallback (misses better reports in lower tiers)
3. **Weighted scoring** (combine tier + content_type + file_size into single score)
   - ❌ Too complex, hard to tune weights, not aligned with v3 spec

**Rationale**:
- ✅ Aligns 100% with v3 enhancement #1 spec
- ✅ Ensures user gets BEST report, not just first report found
- ✅ Separation of concerns (search vs. prioritization vs. download)
- ✅ Testable (mock all providers, verify all `search()` calls made)
- ✅ Fail-open (if one provider search fails, continue with others)

**Consequences**:
- ✅ User gets best available report (higher quality outputs)
- ✅ Clear separation: search → prioritize → download (easy to test each phase)
- ⚠️ Slower than sequential fallback (must search all tiers, not early termination)
- ⚠️ Requires all providers to implement new `search()` interface (migration cost)

**Migration Plan**:
- Phase 1 SEC EDGAR provider: Update `search()` to return `List[SourceRef]`
- Mock providers for Tier 2/3: Implement interface stubs (real implementations in Phase 2b)

---

## ADR-003: Use Pydantic `SourceRef` Model (Not Plain Dicts)

**Status**: Accepted

**Context**:
Need type-safe contract for search results (URL, tier, priority_score, etc.).

**Decision**:
Define `SourceRef` as Pydantic `BaseModel` with validated fields (tier: int [1-3], priority_score: int [0-100], etc.).

**Alternatives Considered**:
1. **TypedDict** (Python 3.8+)
   - ❌ No runtime validation, only static type checking
   - ❌ Doesn't catch invalid priority_score at runtime
2. **Plain dict** (`{"provider": "sec_edgar", "tier": 1, ...}`)
   - ❌ No type safety, no validation, error-prone
3. **dataclass** with manual validation
   - ❌ Verbose (need custom `__post_init__` for validation)
   - ❌ Reinvents Pydantic's validation features

**Rationale**:
- ✅ Runtime validation (catches invalid tier, priority_score at creation time)
- ✅ Type safety (mypy enforces correct types)
- ✅ Immutable (Config.frozen=True prevents accidental mutation)
- ✅ JSON serialization/deserialization (for future API endpoints)
- ✅ Already using Pydantic in project (CompanyRef, CompanyReport)

**Consequences**:
- ✅ Bugs caught at SourceRef creation (not downstream in prioritization)
- ✅ Self-documenting API (Field descriptions via docstrings)
- ⚠️ Slightly slower than plain dicts (validation overhead ~microseconds per object)

---

## ADR-004: Use `@pytest.mark.cp` to Mark Critical Path Tests

**Status**: Accepted

**Context**:
SCA v13.8 TDD Guard requires ≥1 test marked `@pytest.mark.cp` per CP file.

**Decision**:
Mark all tests for `multi_source_crawler.py` and `ingestion_contracts.py` with `@pytest.mark.cp`.

**Alternatives Considered**:
1. **No markers** (rely on test discovery by file name)
   - ❌ Doesn't satisfy SCA v13.8 gate (requires explicit CP marking)
2. **Custom marker** (e.g., `@pytest.mark.critical`)
   - ❌ Not aligned with SCA protocol (expects `@pytest.mark.cp`)

**Rationale**:
- ✅ Satisfies SCA v13.8 TDD Guard requirement
- ✅ Enables selective test execution (`pytest -m cp` runs only CP tests)
- ✅ Clear signal of which tests are critical vs. optional

**Consequences**:
- ✅ MEA validator can verify CP tests exist and pass
- ✅ Faster CI feedback (run CP tests first, optional tests later)

---

## ADR-005: Use Hypothesis for Property-Based Testing of Prioritization

**Status**: Accepted

**Context**:
Prioritization algorithm must work correctly for ALL valid inputs (not just hand-picked examples). Edge cases include: empty lists, ties in priority_score, all same tier, etc.

**Decision**:
Use Hypothesis library with `@given(st.lists(st.builds(SourceRef, ...)))` to generate random candidate lists and verify invariants.

**Alternatives Considered**:
1. **Parameterized tests** (`@pytest.mark.parametrize`)
   - ❌ Requires manually enumerating all edge cases (tedious, error-prone)
2. **Random testing** (custom random input generation)
   - ❌ Reinvents Hypothesis, less shrinking/reporting
3. **No property tests** (only example-based tests)
   - ❌ Doesn't satisfy SCA v13.8 TDD Guard (requires ≥1 Hypothesis test)

**Rationale**:
- ✅ Hypothesis generates hundreds of test cases automatically
- ✅ Finds edge cases developers don't think of (e.g., negative priority_score)
- ✅ Shrinking: when test fails, Hypothesis finds minimal failing input
- ✅ Deterministic (fixed seed via `hypothesis.settings.derandomize=True`)
- ✅ Required by SCA v13.8 protocol

**Consequences**:
- ✅ Higher confidence in algorithm correctness (tested on 100s of inputs, not just 5)
- ✅ Catches bugs that example-based tests miss
- ⚠️ Slower test execution (~1-2 seconds per property test vs. milliseconds for unit test)

**Example**:
```python
@given(st.lists(st.builds(SourceRef, tier=st.integers(1, 3), priority_score=st.integers(0, 100))))
def test_prioritization_always_sorts_by_tier_first(candidates):
    sorted_candidates = crawler._prioritize_candidates(candidates)
    # Verify tier ordering
    for i in range(len(sorted_candidates) - 1):
        assert sorted_candidates[i].tier <= sorted_candidates[i+1].tier
```

---

## ADR-006: Fail-Closed on Download Failure (Raise Exception, Not Return None)

**Status**: Accepted

**Context**:
`download_best_report()` tries all candidates. If ALL fail, what should it do?

**Decision**:
Raise `RuntimeError` with descriptive message (company, year, candidate count, last exception).

**Alternatives Considered**:
1. **Return None**
   - ❌ Silent failure, caller must check for None
   - ❌ Error-prone (caller might forget None check)
2. **Return partial result** (e.g., CompanyReport with empty fields)
   - ❌ Misleading (pretends download succeeded)
   - ❌ Violates SCA authenticity invariant (honest reporting)
3. **Log error and continue** (no exception)
   - ❌ Hides failures from caller

**Rationale**:
- ✅ Fail-fast (caller immediately knows download failed)
- ✅ Honest reporting (aligns with SCA v13.8 Invariant #5)
- ✅ Descriptive error message (includes context for debugging)
- ✅ Forces caller to handle failure explicitly (try-except)

**Consequences**:
- ✅ Bugs surface quickly (no silent failures)
- ✅ Clear error messages for debugging
- ⚠️ Caller must handle exceptions (but this is correct behavior)

---

## ADR-007: Mock Tier 2/3 Providers (Real Implementations in Phase 2b)

**Status**: Accepted

**Context**:
Phase 2 focuses on orchestration logic (search all, prioritize, download best). Implementing real web scrapers (GRI, company IR) would delay validation of core algorithm.

**Decision**:
- Phase 2: Implement mock providers for GRI, company IR (return hardcoded `List[SourceRef]`)
- Phase 2b: Replace mocks with real Playwright-based implementations

**Alternatives Considered**:
1. **Implement real scrapers in Phase 2**
   - ❌ Delays validation of core algorithm (web scraping is complex)
   - ❌ Increases scope of Phase 2 (2-3 days → 1-2 weeks)
2. **Skip Tier 2/3 providers entirely**
   - ❌ Can't test multi-source prioritization (only one tier)
   - ❌ Can't verify fallback behavior

**Rationale**:
- ✅ Reduces Phase 2 scope (focus on orchestration, not scraping)
- ✅ Enables testing of multi-tier prioritization without web scraping complexity
- ✅ Defers risk (web scraping can fail for many reasons, separate from prioritization logic)
- ✅ Phase 2b can add real scrapers incrementally (one provider at a time)

**Consequences**:
- ✅ Phase 2 completes faster (2-3 days, not 1-2 weeks)
- ✅ Core algorithm validated independently of web scraping
- ⚠️ Phase 2b required to get end-to-end multi-source functionality

---

## ADR-008: Use `.coveragerc` to Limit Coverage to CP Files Only

**Status**: Accepted (inherited from Phase 1)

**Context**:
Coverage should measure CP files only (not legacy code, not test files).

**Decision**:
Configure `.coveragerc` with:
```ini
[report]
include =
    agents/crawler/multi_source_crawler.py
    libs/contracts/ingestion_contracts.py
```

**Alternatives Considered**:
1. **Measure coverage on entire codebase**
   - ❌ Inflates metrics with non-CP code (legacy, tests, docs)
   - ❌ Violates SCA v13.8 Invariant #5 (honest reporting)
2. **No coverage configuration**
   - ❌ Same problem as (1)

**Rationale**:
- ✅ Honest measurement (only actively maintained code)
- ✅ Aligns with Phase 1 approach (87% on Phase 1 code only)
- ✅ Satisfies SCA v13.8 protocol

**Consequences**:
- ✅ Coverage metrics are accurate (no skew from legacy code)
- ✅ Clear target (≥95% on 2 files, not entire codebase)

---

## ADR-009: Use `enabled` Flag to Disable Providers (Not Removing from List)

**Status**: Accepted

**Context**:
Need way to temporarily disable providers (e.g., CDP requires credentials, GRI down for maintenance).

**Decision**:
Check `getattr(provider, "enabled", True)` in search loop. If `enabled=False`, skip provider.

**Alternatives Considered**:
1. **Remove provider from tiers list**
   - ❌ Requires modifying code (not configuration)
   - ❌ Can't toggle at runtime
2. **Config file** (e.g., `providers.yaml`)
   - ✅ More flexible, but adds complexity for Phase 2
   - ⏸️ Defer to Phase 2b (use simple flag for now)

**Rationale**:
- ✅ Simple (just set `provider.enabled = False`)
- ✅ Testable (mock disabled providers, verify skipped)
- ✅ Backwards compatible (defaults to `True` if attribute doesn't exist)

**Consequences**:
- ✅ Easy to disable providers for testing
- ✅ No code changes needed (just set attribute)
- ⚠️ Not persistent (resets on process restart, but OK for Phase 2)

---

## ADR-010: Separate Search, Prioritize, Download into 3 Methods (Not 1 Mega-Method)

**Status**: Accepted

**Context**:
Could implement `download_best_report()` as single method doing search + prioritize + download in one function.

**Decision**:
Split into 3 methods:
1. `search_company_reports()` - Returns `List[SourceRef]`
2. `_prioritize_candidates()` - Returns sorted `List[SourceRef]`
3. `download_best_report()` - Calls (1) + (2), then downloads

**Alternatives Considered**:
1. **Single mega-method** (`download_best_report()` does everything)
   - ❌ High CCN (likely >10), violates complexity gate
   - ❌ Hard to test each phase independently
   - ❌ Tight coupling (can't reuse search/prioritize logic)

**Rationale**:
- ✅ Separation of concerns (each method has one job)
- ✅ Testable (can test search, prioritize, download independently)
- ✅ Low complexity (each method CCN ≤3)
- ✅ Reusable (future code can call `search_company_reports()` without downloading)

**Consequences**:
- ✅ Each method is simple (easy to understand, easy to test)
- ✅ Can mock/stub individual methods for testing
- ✅ Satisfies SCA v13.8 complexity gate (CCN ≤10)

---

**Document Prepared By**: Scientific Coding Agent v13.8-MEA
**Review Status**: Ready for implementation
**Total Decisions**: 10 (all accepted)
