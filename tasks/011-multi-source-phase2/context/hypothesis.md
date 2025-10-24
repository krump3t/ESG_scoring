# Phase 2 Hypothesis: Multi-Source Crawler with Priority-Based Download

**Task ID**: 011-multi-source-phase2
**SCA Version**: v13.8-MEA
**Date**: 2025-10-24
**Status**: Planning (Context Gate)
**Depends On**: Phase 1 (010-hybrid-ingestion-phase1) ✅ COMPLETE

---

## Research Question

**Can a multi-source crawler implement comprehensive search across all data tiers (Tier 1A → 3) with priority-based download selection, while maintaining production-grade reliability (retry logic, rate limiting) and honest validation metrics (≥95% coverage)?**

---

## Success Criteria

### Primary Metrics

1. **Search Comprehensiveness**: `search_company_reports()` returns ALL candidates from ALL enabled tiers
   - **Threshold**: 100% of enabled providers searched
   - **Measurement**: Mock all providers, verify all `search()` calls made
   - **Exclusion**: Disabled providers (`enabled=False`) correctly skipped

2. **Prioritization Correctness**: `_prioritize_candidates()` sorts by `(tier, priority_score)` ascending
   - **Threshold**: 100% correct ordering in all test cases
   - **Measurement**: Property-based tests with Hypothesis (generate random candidate lists)
   - **Exclusion**: None (deterministic sorting algorithm)

3. **Download Best Report**: `download_best_report()` attempts download from highest-priority candidate first
   - **Threshold**: ≥95% success rate when best candidate is available
   - **Measurement**: Mock provider downloads, verify call order
   - **Exclusion**: Cases where ALL candidates fail (should raise exception)

4. **Fallback Behavior**: When highest-priority candidate fails, try next candidate
   - **Threshold**: 100% fallback to next candidate on failure
   - **Measurement**: Mock first N providers to raise exceptions, verify (N+1)th called
   - **Exclusion**: None (core requirement)

5. **Provider Interface Compatibility**: All providers implement new `search()` → `List[SourceRef]` contract
   - **Threshold**: 100% of providers return valid `SourceRef` objects
   - **Measurement**: Pydantic validation on all `search()` return values
   - **Exclusion**: Legacy providers marked for deprecation

### Quality Metrics (SCA v13.8 Gates)

6. **Code Coverage (CP Files)**: Line coverage ≥95%, branch coverage ≥95%
   - **CP Files**:
     - `agents/crawler/multi_source_crawler.py`
     - `libs/contracts/ingestion_contracts.py` (SourceRef enhancements)
   - **Measurement**: pytest-cov with `.coveragerc` limiting to CP files only
   - **Exclusion**: Legacy code, external library code

7. **Test Suite Completeness**:
   - ≥1 test marked `@pytest.mark.cp` per CP file
   - ≥3 Hypothesis property tests (prioritization, SourceRef validation, tier ordering)
   - ≥6 failure-path tests (all providers fail, invalid SourceRef, empty candidate list, etc.)
   - **Threshold**: 100% of required test types present
   - **Measurement**: pytest collection analysis

8. **TDD Compliance**: Tests committed to git BEFORE implementation
   - **Threshold**: Git history shows test file created/modified before CP files
   - **Measurement**: `git log --all --pretty=format:"%H %s" -- <file>` timestamp comparison
   - **Exclusion**: Documentation-only commits

9. **Type Safety**: `mypy --strict` produces 0 errors on CP files
   - **Threshold**: 0 type errors
   - **Measurement**: `mypy --strict <cp_file>`
   - **Exclusion**: Third-party library stubs (use `type: ignore` comments sparingly)

10. **Complexity**: Cyclomatic complexity ≤10, cognitive complexity ≤15
    - **Threshold**: All functions pass complexity gates
    - **Measurement**: Lizard analysis
    - **Exclusion**: None (refactor if exceeded)

---

## Critical Path (CP) Definition

**CP Files** (must achieve ≥95% coverage):
1. `agents/crawler/multi_source_crawler.py`
   - `MultiSourceCrawler.search_company_reports()` - Search all tiers
   - `MultiSourceCrawler._prioritize_candidates()` - Sort by (tier, priority_score)
   - `MultiSourceCrawler.download_best_report()` - Download with fallback

2. `libs/contracts/ingestion_contracts.py` (SourceRef enhancements)
   - `SourceRef.priority_score` - New field for prioritization
   - `SourceRef` model validation

**Non-CP Files** (excluded from coverage requirements):
- `agents/crawler/data_providers/base_provider.py` - Already tested in Phase 1
- Test files - Not counted in coverage
- Documentation - Checked by `interrogate`, not coverage

---

## Data Strategy

### Input Data

**Source**: Mock provider responses (no real API calls in unit tests)

**Splits**:
- **Unit tests**: 100% mocked providers (responses library)
- **Integration tests**: Real SEC EDGAR API + mocked web scrapers (marked `@pytest.mark.integration`)
- **E2E tests**: Real multi-source download (marked `@pytest.mark.e2e`, not run in CI)

**Normalization**:
- All providers return `List[SourceRef]` with standardized fields
- `priority_score` normalized: 0-100 scale (0 = highest priority)
- `tier` normalized: 1-3 (1 = highest quality)

**Leakage Guards**:
- No test data derived from production data
- All mock responses hand-crafted or generated with fixed seeds
- No circular dependencies (crawler doesn't call itself)

### Output Data

**Artifacts**:
- `qa/coverage.xml` - Coverage report (≥95% on CP files)
- `qa/htmlcov/` - HTML coverage visualization
- `qa/mypy.txt` - Type safety report (0 errors)
- `qa/lizard_report.txt` - Complexity analysis
- `qa/pytest.txt` - Test execution log

**Validation**:
- Coverage gate: pytest-cov enforces ≥95%
- Type gate: mypy enforces strict mode
- Complexity gate: Lizard enforces CCN ≤10

---

## Verification Plan

### Differential Tests

**Test**: Phase 1 SEC EDGAR provider still works with Phase 2 multi-source crawler

```python
def test_phase1_provider_works_with_phase2_crawler():
    """Ensure Phase 1 SEC EDGAR provider compatible with Phase 2 crawler."""
    crawler = MultiSourceCrawler(providers=[sec_edgar_provider])
    candidates = crawler.search_company_reports(company=CompanyRef(cik="0000320193"), year=2023)

    assert len(candidates) > 0
    assert all(isinstance(c, SourceRef) for c in candidates)
    assert all(c.tier == 1 for c in candidates)  # SEC EDGAR is Tier 1
```

**Expected**: No breaking changes to Phase 1 functionality

### Sensitivity Tests

**Test 1**: Prioritization is stable (deterministic)

```python
@given(st.lists(st.builds(SourceRef, ...)))
def test_prioritization_is_deterministic(candidates):
    """Ensure sort order is deterministic for same input."""
    sorted1 = crawler._prioritize_candidates(candidates)
    sorted2 = crawler._prioritize_candidates(candidates)
    assert sorted1 == sorted2
```

**Test 2**: Fallback behavior is robust to partial failures

```python
def test_fallback_handles_N_failures():
    """Test fallback when first N providers fail."""
    for n in [1, 2, 3, 4]:
        # Mock first n providers to raise exceptions
        # Verify (n+1)th provider called
        ...
```

**Expected**: Crawler tries all candidates until one succeeds

### Property-Based Tests (Hypothesis)

**Test 1**: Prioritization always sorts by tier first, then priority_score

```python
@given(st.lists(st.builds(SourceRef, tier=st.integers(1, 3), priority_score=st.integers(0, 100))))
def test_prioritization_tier_first(candidates):
    """Tier takes precedence over priority_score."""
    sorted_candidates = crawler._prioritize_candidates(candidates)

    # Verify tier ordering
    for i in range(len(sorted_candidates) - 1):
        assert sorted_candidates[i].tier <= sorted_candidates[i+1].tier

        # Within same tier, priority_score is sorted
        if sorted_candidates[i].tier == sorted_candidates[i+1].tier:
            assert sorted_candidates[i].priority_score <= sorted_candidates[i+1].priority_score
```

**Test 2**: SourceRef validation rejects invalid priority_scores

```python
@given(st.integers())
def test_source_ref_validates_priority_score(score):
    """Priority score must be 0-100."""
    if 0 <= score <= 100:
        SourceRef(provider="test", tier=1, priority_score=score)  # Should succeed
    else:
        with pytest.raises(ValidationError):
            SourceRef(provider="test", tier=1, priority_score=score)  # Should fail
```

---

## Power Analysis & Confidence Intervals

**Sample Size**: Not applicable (deterministic algorithm, not statistical model)

**Effect Size**: Not applicable (100% correct ordering or failure)

**Confidence**: 100% via comprehensive test coverage (property-based + failure-path tests)

**Statistical Plan**: N/A (this is deterministic software, not hypothesis testing)

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Provider interface changes break Phase 1** | Medium | High | Differential tests, backward compatibility layer |
| **Prioritization logic too complex (CCN >10)** | Low | Medium | Extract `_sort_key()` helper function if needed |
| **Mock providers don't match real behavior** | Medium | Medium | Integration tests with real SEC EDGAR API |
| **Coverage <95% due to edge cases** | Low | High | TDD-first approach, property-based tests for edge cases |
| **Type errors from Pydantic model changes** | Low | Medium | `mypy --strict` enforced, type stubs for Pydantic |

---

## Exclusions

**Not in Phase 2 Scope**:
1. Asymmetric extraction paths (JSON vs PDF) - Phase 3
2. Pydantic-Parquet 1:1 parity - Phase 3
3. Dagster orchestration - Phase 4
4. Real web scraping (Playwright) - Deferred to Phase 2b (focus on orchestration logic first)
5. CDP/GRI provider implementations - Mock interfaces only (real implementations in Phase 2b)

**Why Excluded**:
- Phase 2 focuses on **orchestration logic** (search all, prioritize, download best)
- Web scraping complexity would delay core algorithm validation
- Actual provider implementations can be added incrementally after orchestration is proven

---

## Dependencies

**Upstream (Blocking)**:
- ✅ Phase 1 (010-hybrid-ingestion-phase1) - SEC EDGAR provider with retry + rate limiting

**Downstream (Dependent on this phase)**:
- Phase 2b: Real web scraper implementations (GRI, company IR)
- Phase 3: Asymmetric extraction paths
- Phase 4: Dagster orchestration

---

## Timeline

**Estimated Duration**: 2-3 days

**Breakdown**:
- Day 1: Context gate (7 files) + TDD tests (24 tests) - 8 hours
- Day 2: Implementation (multi_source_crawler.py, SourceRef) - 6 hours
- Day 3: Validation (MEA loop, coverage, snapshot save) - 4 hours

**Total**: 18-20 hours

---

## Alignment with v3 Enhancement Roadmap

**Reference**: `tasks/010-hybrid-ingestion-phase1/V3_ENHANCEMENT_ROADMAP.md`

**v3 Enhancement #1**: Priority-Based Multi-Source Download

**Phase 2 Delivers**:
- ✅ Search ALL tiers (not sequential fallback)
- ✅ Prioritize candidates by `(tier, priority_score)`
- ✅ Download best candidate with fallback to next on failure
- ✅ Provider interface supports `SourceRef` return type

**Alignment**: 100% aligned with v3 Enhancement #1 requirements

---

**Document Prepared By**: Scientific Coding Agent v13.8-MEA
**Review Status**: Ready for implementation
**Next Action**: Complete context gate (6 remaining files) → Write TDD tests → Implement
