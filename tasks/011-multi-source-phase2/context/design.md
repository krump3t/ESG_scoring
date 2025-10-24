# Phase 2 Technical Design: Multi-Source Crawler

**Task ID**: 011-multi-source-phase2
**SCA Version**: v13.8-MEA
**Date**: 2025-10-24
**Status**: Planning (Context Gate)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ MultiSourceCrawler (Orchestration Layer)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  search_company_reports(company, year)                      │
│    ↓                                                        │
│  [Provider 1, Provider 2, Provider 3, ...]                  │
│    ↓                                                        │
│  [SourceRef, SourceRef, SourceRef, ...]                     │
│    ↓                                                        │
│  _prioritize_candidates(candidates)                         │
│    ↓                                                        │
│  Sorted[SourceRef] (by tier, priority_score)                │
│    ↓                                                        │
│  download_best_report(company, year)                        │
│    ↓                                                        │
│  Try download from sorted[0], if fail → sorted[1], ...      │
│    ↓                                                        │
│  CompanyReport (first successful download)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Provider Layer (Phase 1 + Mocks)                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SECEdgarProvider (Phase 1 - Real)                          │
│    - search() → List[SourceRef]                             │
│    - download(source_ref) → CompanyReport                   │
│                                                             │
│  GRIProvider (Phase 2 - Mock)                               │
│    - search() → List[SourceRef]                             │
│    - download(source_ref) → CompanyReport                   │
│                                                             │
│  CompanyIRProvider (Phase 2 - Mock)                         │
│    - search() → List[SourceRef]                             │
│    - download(source_ref) → CompanyReport                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Search Phase (Comprehensive)

```python
def search_company_reports(self, company: CompanyRef, year: int) -> List[SourceRef]:
    """Search ALL tiers, return complete candidate list."""

    all_candidates: List[SourceRef] = []

    for tier_index, providers in enumerate(self.tiers):
        for provider in providers:
            # Skip disabled providers
            if not getattr(provider, "enabled", True):
                logger.info(f"Skipping disabled provider: {provider.__class__.__name__}")
                continue

            try:
                # Call provider's search method
                tier_candidates = provider.search(company, year, tier=tier_index + 1)

                # Validate all SourceRef objects
                for candidate in tier_candidates:
                    if not isinstance(candidate, SourceRef):
                        raise TypeError(f"Provider {provider} returned non-SourceRef: {type(candidate)}")

                all_candidates.extend(tier_candidates)
                logger.info(f"Provider {provider.__class__.__name__} found {len(tier_candidates)} candidates")

            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} search failed: {e}")
                # Continue to next provider (don't fail entire search)
                continue

    logger.info(f"Total candidates found: {len(all_candidates)} across {len(self.tiers)} tiers")
    return all_candidates
```

**Key Design Decisions**:
- ✅ **Fail-open**: If one provider fails, continue searching others
- ✅ **Type validation**: Ensure all providers return valid `SourceRef` objects
- ✅ **Logging**: Structured logging for observability
- ✅ **Tier-agnostic**: Doesn't assume tier ordering (prioritization happens later)

---

### 2. Prioritization Phase (Sorting)

```python
def _prioritize_candidates(self, candidates: List[SourceRef]) -> List[SourceRef]:
    """Sort candidates by (tier, priority_score) ascending.

    Lower tier = higher quality (1 > 2 > 3)
    Lower priority_score = higher priority (10 > 20 > 30)

    Examples:
        SourceRef(tier=1, priority=10) comes before SourceRef(tier=1, priority=20)
        SourceRef(tier=1, priority=50) comes before SourceRef(tier=2, priority=10)
    """

    if not candidates:
        return []

    # Stable sort (preserves order of equal elements)
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (c.tier, c.priority_score)
    )

    logger.debug(f"Prioritized {len(sorted_candidates)} candidates:")
    for i, candidate in enumerate(sorted_candidates[:5]):  # Log top 5
        logger.debug(f"  {i+1}. Tier {candidate.tier}, Priority {candidate.priority_score} - {candidate.provider}")

    return sorted_candidates
```

**Key Design Decisions**:
- ✅ **Deterministic**: Stable sort ensures reproducible ordering
- ✅ **Simple algorithm**: Single `sorted()` call (CCN = 1, easy to test)
- ✅ **Empty list handling**: Returns `[]` instead of raising exception
- ✅ **Observability**: Debug logs for top 5 candidates

**Complexity**: O(n log n) where n = number of candidates (acceptable for n < 1000)

---

### 3. Download Phase (Fallback)

```python
def download_best_report(self, company: CompanyRef, year: int) -> CompanyReport:
    """Download best report with fallback to next candidate on failure.

    Raises:
        RuntimeError: If no candidates found or all downloads fail
    """

    # Step 1: Search all tiers
    all_candidates = self.search_company_reports(company, year)

    if not all_candidates:
        raise RuntimeError(
            f"No report candidates found for {company.name} ({year}). "
            f"Searched {sum(len(tier) for tier in self.tiers)} providers across {len(self.tiers)} tiers."
        )

    # Step 2: Prioritize candidates
    sorted_candidates = self._prioritize_candidates(all_candidates)

    # Step 3: Try download from best candidate first, fallback on failure
    last_exception = None

    for i, source_ref in enumerate(sorted_candidates):
        try:
            provider = self._get_provider(source_ref.provider)

            if not provider:
                logger.warning(f"Provider {source_ref.provider} not found, skipping")
                continue

            logger.info(
                f"Attempting download (rank {i+1}/{len(sorted_candidates)}): "
                f"{source_ref.provider} (tier={source_ref.tier}, priority={source_ref.priority_score})"
            )

            report = provider.download(source_ref, company, year)

            logger.info(f"Successfully downloaded report from {source_ref.provider}")
            return report

        except Exception as e:
            last_exception = e
            logger.warning(
                f"Download failed from {source_ref.provider} (rank {i+1}): {e}"
            )
            # Continue to next candidate

    # All downloads failed
    raise RuntimeError(
        f"Failed to download report for {company.name} ({year}) after trying "
        f"{len(sorted_candidates)} candidates. Last error: {last_exception}"
    )
```

**Key Design Decisions**:
- ✅ **Fail-closed**: Raises exception if all downloads fail (don't return partial data)
- ✅ **Observability**: Log each download attempt with rank
- ✅ **Context in errors**: Include company, year, candidate count in exception messages
- ✅ **Fallback limit**: Tries ALL candidates (no arbitrary cutoff)

---

## Provider Interface Contract

### Enhanced `BaseDataProvider`

```python
# agents/crawler/data_providers/base_provider.py

from typing import List, Optional
from libs.contracts.ingestion_contracts import CompanyRef, SourceRef, CompanyReport

class BaseDataProvider:
    """Base class for data providers.

    Phase 2 Enhancement: search() now returns List[SourceRef] instead of List[str]
    """

    def search(
        self,
        company: CompanyRef,
        year: int,
        tier: int
    ) -> List[SourceRef]:
        """Search for reports matching company and year.

        Args:
            company: Company reference (name, CIK, etc.)
            year: Fiscal year
            tier: Provider's tier (1-3) for populating SourceRef

        Returns:
            List of SourceRef objects (URLs, priority scores, etc.)

        Example:
            >>> provider.search(CompanyRef(cik="0000320193"), 2023, tier=1)
            [
                SourceRef(provider="sec_edgar", tier=1, url="...", priority_score=10),
                SourceRef(provider="sec_edgar", tier=1, url="...", priority_score=20),
            ]
        """
        raise NotImplementedError

    def download(
        self,
        source_ref: SourceRef,
        company: CompanyRef,
        year: int
    ) -> CompanyReport:
        """Download report from source reference.

        Args:
            source_ref: SourceRef from search() method
            company: Company reference
            year: Fiscal year

        Returns:
            CompanyReport with local_path, sha256, etc.

        Raises:
            DocumentNotFoundError: If report not found (404)
            RateLimitExceededError: If rate limit exceeded (503)
            RequestTimeoutError: If request times out
        """
        raise NotImplementedError
```

**Migration from Phase 1**:
- **Before**: `search()` returned `List[str]` (URLs)
- **After**: `search()` returns `List[SourceRef]` (structured objects)
- **Compatibility**: Phase 1 SEC EDGAR provider will be updated with adapter pattern

---

## SourceRef Enhancements

```python
# libs/contracts/ingestion_contracts.py

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Literal, Optional

class SourceRef(BaseModel):
    """Reference to a data source (URL, API endpoint, etc.)

    Phase 2 Enhancement: Added priority_score for prioritization logic
    """

    provider: str = Field(..., description="Provider name (e.g., 'sec_edgar', 'gri')")

    tier: int = Field(
        ...,
        ge=1,
        le=3,
        description="Quality tier (1=highest, 2=medium, 3=lowest)"
    )

    url: Optional[HttpUrl] = Field(None, description="Download URL (if applicable)")

    access: Literal["api", "scrape", "file"] = Field(
        "api",
        description="Access method (api=REST API, scrape=web scraping, file=local file)"
    )

    content_type: str = Field(
        ...,
        description="MIME type (e.g., 'application/pdf', 'text/html', 'application/json')"
    )

    priority_score: int = Field(
        100,
        ge=0,
        le=100,
        description="Priority score (0=highest, 100=lowest). Lower is better."
    )

    @validator("priority_score")
    def validate_priority_score(cls, v):
        """Ensure priority_score is in valid range."""
        if not (0 <= v <= 100):
            raise ValueError(f"priority_score must be 0-100, got {v}")
        return v

    class Config:
        """Pydantic config."""
        frozen = True  # Immutable (hashable for deduplication)
```

**Priority Score Examples**:
```python
# Tier 1 sources
SourceRef(provider="sec_edgar", tier=1, content_type="application/pdf", priority_score=10)  # 10-K PDF (best)
SourceRef(provider="sec_edgar", tier=1, content_type="text/html", priority_score=20)        # 10-K HTML
SourceRef(provider="sec_edgar", tier=1, content_type="application/json", priority_score=5)  # XBRL JSON (structured)

# Tier 2 sources
SourceRef(provider="gri", tier=2, content_type="application/pdf", priority_score=30)        # GRI database PDF
SourceRef(provider="gri", tier=2, content_type="text/html", priority_score=40)              # GRI database HTML

# Tier 3 sources
SourceRef(provider="company_ir", tier=3, content_type="application/pdf", priority_score=50) # Company IR PDF
SourceRef(provider="company_ir", tier=3, content_type="text/html", priority_score=60)       # Company IR HTML
```

---

## Data Strategy (from hypothesis.md)

### Normalization

**Input**: Provider-specific search results
**Output**: Standardized `SourceRef` objects

**Normalization Rules**:
1. **Tier**: Provider declares tier (1-3) when implementing interface
2. **Priority Score**: Provider assigns based on content type:
   - JSON/XBRL: 0-10 (structured data, highest priority)
   - PDF: 10-30 (semi-structured, medium priority)
   - HTML: 30-60 (unstructured, lower priority)
3. **Content Type**: MIME type from HTTP headers or file extension

### Leakage Guards

**No Data Leakage Between Phases**:
- Unit tests use 100% mocked providers
- Integration tests call real SEC EDGAR API (Phase 1) + mocked others
- E2E tests marked separately (`@pytest.mark.e2e`, not run in CI)

**No Circular Dependencies**:
- Crawler calls providers, providers never call crawler
- Providers don't share state (each has own rate limiter)

---

## Verification Plan (from hypothesis.md)

### Differential Tests

**Test**: Phase 1 SEC EDGAR provider works with Phase 2 crawler

```python
@pytest.mark.cp
def test_phase1_provider_compatible_with_phase2_crawler():
    """Ensure Phase 1 SEC EDGAR provider works with Phase 2 crawler."""
    # Use real Phase 1 provider (not mocked)
    sec_provider = SECEdgarProvider(contact_email="test@example.com")

    # Wrap in Phase 2 crawler
    crawler = MultiSourceCrawler(tiers=[[sec_provider]])

    # Search for Apple 2023 10-K
    candidates = crawler.search_company_reports(
        company=CompanyRef(cik="0000320193", name="Apple Inc."),
        year=2023
    )

    # Verify results
    assert len(candidates) > 0, "No candidates found"
    assert all(isinstance(c, SourceRef) for c in candidates), "Not all SourceRef"
    assert all(c.tier == 1 for c in candidates), "SEC EDGAR should be tier 1"
    assert all(c.provider == "sec_edgar" for c in candidates), "Wrong provider name"
```

### Sensitivity Tests

**Test**: Fallback behavior is robust to partial failures

```python
@pytest.mark.cp
@pytest.mark.parametrize("num_failures", [0, 1, 2, 3, 4])
def test_fallback_handles_n_failures(num_failures):
    """Test fallback when first N providers fail."""
    # Create 5 mock providers
    providers = [MagicMock() for _ in range(5)]

    # Mock first N to raise exceptions
    for i in range(num_failures):
        providers[i].download.side_effect = RequestTimeoutError("Timeout")

    # Mock (N+1)th to succeed
    if num_failures < 5:
        providers[num_failures].download.return_value = CompanyReport(...)

    crawler = MultiSourceCrawler(tiers=[providers])

    if num_failures < 5:
        # Should succeed by calling (N+1)th provider
        report = crawler.download_best_report(...)
        assert providers[num_failures].download.called
    else:
        # All failed, should raise
        with pytest.raises(RuntimeError, match="Failed to download"):
            crawler.download_best_report(...)
```

---

## Success Thresholds (from hypothesis.md)

| Metric | Threshold | Justification |
|--------|-----------|---------------|
| **Search Comprehensiveness** | 100% providers called | Core requirement (must search ALL tiers) |
| **Prioritization Correctness** | 100% correct ordering | Deterministic algorithm (property-based tests) |
| **Download Success Rate** | ≥95% | When best candidate available, should succeed |
| **Fallback Correctness** | 100% | Must try next candidate on failure |
| **Coverage (CP Files)** | ≥95% line, ≥95% branch | SCA v13.8 gate |
| **Type Safety** | 0 mypy errors | SCA v13.8 gate |
| **Complexity** | CCN ≤10, Cognitive ≤15 | SCA v13.8 gate |

---

## Implementation Timeline

**Day 1** (8 hours):
- ✅ Context gate (7 files) - 2 hours
- ✅ TDD tests (24 tests) - 6 hours

**Day 2** (6 hours):
- ✅ `libs/contracts/ingestion_contracts.py` - SourceRef enhancements - 1 hour
- ✅ `agents/crawler/multi_source_crawler.py` - Implementation - 4 hours
- ✅ Phase 1 provider adapter (if needed) - 1 hour

**Day 3** (4 hours):
- ✅ MEA validation loop (fix issues) - 2 hours
- ✅ Coverage verification (≥95%) - 1 hour
- ✅ Snapshot save - 1 hour

**Total**: 18 hours over 2-3 days

---

**Document Prepared By**: Scientific Coding Agent v13.8-MEA
**Review Status**: Ready for implementation
**Next Action**: Complete context gate (5 remaining files) → Write TDD tests
