"""
Comprehensive Test Suite for MultiSourceCrawler Phase 2 (v3 Enhancement #1)

**TDD Approach**: These tests are written BEFORE implementation.
**SCA v13.8 Compliance**:
- ≥1 test marked @pytest.mark.cp per CP file
- ≥3 Hypothesis property tests
- ≥6 failure-path tests
- ≥95% coverage target on multi_source_crawler.py

**Test Categories**:
1. Unit Tests (10): Mocked providers, search/prioritize/download logic
2. Property Tests (3): Hypothesis-based invariant verification
3. Failure-Path Tests (6): All error conditions
4. Integration Tests (2): Real SEC EDGAR provider compatibility
5. Differential Tests (1): Phase 1 compatibility
6. Sensitivity Tests (2): Fallback robustness

Total: 24 tests

**Phase 2 Focus**: Priority-based multi-source download
- Search ALL tiers comprehensively (not sequential fallback)
- Prioritize by (tier, priority_score)
- Download best candidate with fallback on failure
"""

import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings
from typing import List

# Imports will be available after implementation
# Using try-except to allow tests to be committed before implementation
try:
    from agents.crawler.multi_source_crawler import MultiSourceCrawler
    from libs.contracts.ingestion_contracts import CompanyRef, SourceRef, CompanyReport
    from agents.crawler.data_providers.exceptions import (
        DocumentNotFoundError,
        RateLimitExceededError,
        RequestTimeoutError
    )
except ImportError:
    # Tests can be written before implementation exists
    # pytest will skip these tests if imports fail
    pytestmark = pytest.mark.skip(reason="Implementation not yet available - TDD mode")


# ============================================================================
# UNIT TESTS (Mocked Providers)
# ============================================================================

@pytest.mark.cp
def test_search_company_reports_calls_all_enabled_providers():
    """Test that search_company_reports() calls ALL enabled providers."""
    # Arrange: Create 3 mock providers
    provider1 = MagicMock()
    provider1.enabled = True
    provider1.search.return_value = [
        SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10)
    ]

    provider2 = MagicMock()
    provider2.enabled = True
    provider2.search.return_value = [
        SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=30)
    ]

    provider3 = MagicMock()
    provider3.enabled = True
    provider3.search.return_value = [
        SourceRef(provider="provider3", tier=3, content_type="application/pdf", priority_score=50)
    ]

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2], [provider3]])
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    candidates = crawler.search_company_reports(company, year=2023)

    # Assert: All providers were called
    assert provider1.search.called
    assert provider2.search.called
    assert provider3.search.called

    # Assert: All candidates returned
    assert len(candidates) == 3
    assert all(isinstance(c, SourceRef) for c in candidates)


@pytest.mark.cp
def test_search_skips_disabled_providers():
    """Test that search_company_reports() skips disabled providers."""
    # Arrange: Provider with enabled=False
    disabled_provider = MagicMock()
    disabled_provider.enabled = False
    disabled_provider.search.return_value = [
        SourceRef(provider="disabled", tier=1, content_type="application/pdf", priority_score=10)
    ]

    enabled_provider = MagicMock()
    enabled_provider.enabled = True
    enabled_provider.search.return_value = [
        SourceRef(provider="enabled", tier=1, content_type="application/pdf", priority_score=20)
    ]

    crawler = MultiSourceCrawler(tiers=[[disabled_provider, enabled_provider]])
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    candidates = crawler.search_company_reports(company, year=2023)

    # Assert: Disabled provider NOT called
    assert not disabled_provider.search.called

    # Assert: Enabled provider WAS called
    assert enabled_provider.search.called

    # Assert: Only enabled provider's candidate returned
    assert len(candidates) == 1
    assert candidates[0].provider == "enabled"


@pytest.mark.cp
def test_search_continues_on_provider_failure():
    """Test that search continues if one provider fails (fail-open)."""
    # Arrange: Provider that raises exception
    failing_provider = MagicMock()
    failing_provider.enabled = True
    failing_provider.search.side_effect = RequestTimeoutError("Network timeout")

    working_provider = MagicMock()
    working_provider.enabled = True
    working_provider.search.return_value = [
        SourceRef(provider="working", tier=1, content_type="application/pdf", priority_score=10)
    ]

    crawler = MultiSourceCrawler(tiers=[[failing_provider, working_provider]])
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    candidates = crawler.search_company_reports(company, year=2023)

    # Assert: Both providers were attempted
    assert failing_provider.search.called
    assert working_provider.search.called

    # Assert: Working provider's candidate returned (failure didn't crash search)
    assert len(candidates) == 1
    assert candidates[0].provider == "working"


@pytest.mark.cp
def test_prioritize_candidates_sorts_by_tier_then_priority_score():
    """Test that _prioritize_candidates() sorts by (tier, priority_score)."""
    # Arrange: Unsorted candidates
    candidates = [
        SourceRef(provider="p1", tier=2, content_type="text/html", priority_score=30),  # Rank 4
        SourceRef(provider="p2", tier=1, content_type="application/pdf", priority_score=20),  # Rank 2
        SourceRef(provider="p3", tier=1, content_type="application/json", priority_score=5),  # Rank 1 (best)
        SourceRef(provider="p4", tier=3, content_type="text/html", priority_score=10),  # Rank 5
        SourceRef(provider="p5", tier=1, content_type="text/html", priority_score=25),  # Rank 3
    ]

    crawler = MultiSourceCrawler(tiers=[])

    # Act
    sorted_candidates = crawler._prioritize_candidates(candidates)

    # Assert: Correct ordering (tier first, then priority_score)
    assert sorted_candidates[0].provider == "p3"  # tier=1, priority=5
    assert sorted_candidates[1].provider == "p2"  # tier=1, priority=20
    assert sorted_candidates[2].provider == "p5"  # tier=1, priority=25
    assert sorted_candidates[3].provider == "p1"  # tier=2, priority=30
    assert sorted_candidates[4].provider == "p4"  # tier=3, priority=10


@pytest.mark.cp
def test_prioritize_handles_empty_list():
    """Test that _prioritize_candidates() handles empty list gracefully."""
    crawler = MultiSourceCrawler(tiers=[])

    # Act
    sorted_candidates = crawler._prioritize_candidates([])

    # Assert: Returns empty list (not None, not exception)
    assert sorted_candidates == []


@pytest.mark.cp
def test_download_best_report_tries_candidates_in_priority_order():
    """Test that download_best_report() tries candidates in sorted order."""
    # Arrange: 3 providers, best one succeeds
    provider1 = MagicMock()  # tier=1, priority=10 (best)
    provider1.search.return_value = [
        SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1")
    ]
    provider1.download.return_value = CompanyReport(
        company=CompanyRef(cik="0000320193", name="Apple Inc."),
        year=2023,
        source=SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10),
        local_path="/tmp/report.pdf",
        sha256="abc123"
    )

    provider2 = MagicMock()  # tier=2, priority=20 (second best)
    provider2.search.return_value = [
        SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20, url="http://example.com/2")
    ]

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2]])
    crawler._get_provider = lambda name: provider1 if name == "provider1" else provider2

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    report = crawler.download_best_report(company, year=2023)

    # Assert: Provider1 (best) was called, provider2 NOT called (didn't need fallback)
    assert provider1.download.called
    assert not provider2.download.called

    # Assert: Correct report returned
    assert report.source.provider == "provider1"


@pytest.mark.cp
def test_download_falls_back_to_next_candidate_on_failure():
    """Test that download_best_report() falls back to next candidate if first fails."""
    # Arrange: First provider fails, second succeeds
    provider1 = MagicMock()  # tier=1, priority=10 (best, but fails)
    provider1.search.return_value = [
        SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1")
    ]
    provider1.download.side_effect = RequestTimeoutError("Timeout")

    provider2 = MagicMock()  # tier=2, priority=20 (fallback, succeeds)
    provider2.search.return_value = [
        SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20, url="http://example.com/2")
    ]
    provider2.download.return_value = CompanyReport(
        company=CompanyRef(cik="0000320193", name="Apple Inc."),
        year=2023,
        source=SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20),
        local_path="/tmp/report.html",
        sha256="def456"
    )

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2]])
    crawler._get_provider = lambda name: provider1 if name == "provider1" else provider2

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    report = crawler.download_best_report(company, year=2023)

    # Assert: Both providers attempted
    assert provider1.download.called
    assert provider2.download.called

    # Assert: Fallback provider's report returned
    assert report.source.provider == "provider2"


@pytest.mark.cp
def test_get_provider_returns_correct_provider_by_name():
    """Test that _get_provider() returns provider matching name."""
    # Arrange
    provider1 = MagicMock()
    provider1.__class__.__name__ = "SECEdgarProvider"

    provider2 = MagicMock()
    provider2.__class__.__name__ = "GRIProvider"

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2]])

    # Act & Assert
    assert crawler._get_provider("SECEdgarProvider") == provider1
    assert crawler._get_provider("GRIProvider") == provider2
    assert crawler._get_provider("NonexistentProvider") is None


@pytest.mark.cp
def test_search_validates_all_source_refs_are_valid():
    """Test that search_company_reports() validates all SourceRef objects."""
    # Arrange: Provider that returns non-SourceRef object
    bad_provider = MagicMock()
    bad_provider.enabled = True
    bad_provider.search.return_value = [
        "not a SourceRef object",  # Invalid return type
    ]

    crawler = MultiSourceCrawler(tiers=[[bad_provider]])
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act: Should log warning and skip invalid candidate (fail-open)
    candidates = crawler.search_company_reports(company, year=2023)

    # Assert: Invalid candidate filtered out
    assert len(candidates) == 0  # Bad provider's invalid return was rejected


@pytest.mark.cp
def test_download_best_report_returns_first_successful_download():
    """Test that download stops after first successful download (doesn't try all candidates)."""
    # Arrange: 3 providers, all would succeed (should stop after first)
    provider1 = MagicMock()
    provider1.search.return_value = [
        SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1")
    ]
    provider1.download.return_value = CompanyReport(
        company=CompanyRef(cik="0000320193", name="Apple Inc."),
        year=2023,
        source=SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10),
        local_path="/tmp/report1.pdf",
        sha256="abc123"
    )

    provider2 = MagicMock()
    provider2.search.return_value = [
        SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20, url="http://example.com/2")
    ]

    provider3 = MagicMock()
    provider3.search.return_value = [
        SourceRef(provider="provider3", tier=3, content_type="application/pdf", priority_score=30, url="http://example.com/3")
    ]

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2], [provider3]])
    crawler._get_provider = lambda name: {"provider1": provider1, "provider2": provider2, "provider3": provider3}.get(name)

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    report = crawler.download_best_report(company, year=2023)

    # Assert: Only provider1 called (stopped after first success)
    assert provider1.download.called
    assert not provider2.download.called
    assert not provider3.download.called

    # Assert: First provider's report returned
    assert report.source.provider == "provider1"


# ============================================================================
# PROPERTY-BASED TESTS (Hypothesis)
# ============================================================================

@pytest.mark.cp
@pytest.mark.hypothesis
@given(st.lists(
    st.builds(
        SourceRef,
        provider=st.text(min_size=1, max_size=20),
        tier=st.integers(min_value=1, max_value=3),
        content_type=st.sampled_from(["application/pdf", "text/html", "application/json"]),
        priority_score=st.integers(min_value=0, max_value=100),
        url=st.none()  # URL is optional
    ),
    min_size=0,
    max_size=50
))
@settings(max_examples=100, deadline=5000)
def test_prioritization_invariant_tier_ordering(candidates):
    """Property test: Prioritization ALWAYS sorts by tier first (tier 1 before tier 2 before tier 3)."""
    crawler = MultiSourceCrawler(tiers=[])

    # Act
    sorted_candidates = crawler._prioritize_candidates(candidates)

    # Assert: Tier ordering invariant
    for i in range(len(sorted_candidates) - 1):
        current_tier = sorted_candidates[i].tier
        next_tier = sorted_candidates[i + 1].tier

        # Tier should be non-decreasing (tier N <= tier N+1)
        assert current_tier <= next_tier, \
            f"Tier ordering violated: tier {current_tier} followed by tier {next_tier}"

        # Within same tier, priority_score should be non-decreasing
        if current_tier == next_tier:
            assert sorted_candidates[i].priority_score <= sorted_candidates[i + 1].priority_score, \
                f"Priority ordering violated within tier {current_tier}"


@pytest.mark.cp
@pytest.mark.hypothesis
@given(st.lists(
    st.builds(
        SourceRef,
        provider=st.text(min_size=1, max_size=20),
        tier=st.integers(min_value=1, max_value=3),
        content_type=st.text(min_size=1),
        priority_score=st.integers(min_value=0, max_value=100),
        url=st.none()
    ),
    min_size=0,
    max_size=50
))
@settings(max_examples=100, deadline=5000)
def test_prioritization_is_deterministic(candidates):
    """Property test: Prioritization is deterministic (same input → same output)."""
    crawler = MultiSourceCrawler(tiers=[])

    # Act: Sort twice
    sorted1 = crawler._prioritize_candidates(candidates)
    sorted2 = crawler._prioritize_candidates(candidates)

    # Assert: Both sorts produce identical results
    assert sorted1 == sorted2, "Prioritization is not deterministic"


@pytest.mark.cp
@pytest.mark.hypothesis
@given(st.integers())
def test_source_ref_rejects_invalid_priority_score(score):
    """Property test: SourceRef validation rejects priority_score outside [0, 100]."""
    if 0 <= score <= 100:
        # Valid score - should succeed
        source_ref = SourceRef(
            provider="test",
            tier=1,
            content_type="application/pdf",
            priority_score=score
        )
        assert source_ref.priority_score == score
    else:
        # Invalid score - should raise ValidationError
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            SourceRef(
                provider="test",
                tier=1,
                content_type="application/pdf",
                priority_score=score
            )


# ============================================================================
# FAILURE-PATH TESTS
# ============================================================================

@pytest.mark.cp
def test_download_raises_exception_when_no_candidates_found():
    """Failure path: download_best_report() raises RuntimeError if no candidates found."""
    # Arrange: All providers return empty lists
    empty_provider = MagicMock()
    empty_provider.enabled = True
    empty_provider.search.return_value = []

    crawler = MultiSourceCrawler(tiers=[[empty_provider]])
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act & Assert: Raises RuntimeError with descriptive message
    with pytest.raises(RuntimeError, match="No report candidates found"):
        crawler.download_best_report(company, year=2023)


@pytest.mark.cp
def test_download_raises_exception_when_all_downloads_fail():
    """Failure path: download_best_report() raises RuntimeError if ALL downloads fail."""
    # Arrange: All providers fail download
    provider1 = MagicMock()
    provider1.search.return_value = [
        SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1")
    ]
    provider1.download.side_effect = RequestTimeoutError("Timeout")

    provider2 = MagicMock()
    provider2.search.return_value = [
        SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20, url="http://example.com/2")
    ]
    provider2.download.side_effect = DocumentNotFoundError("404 Not Found")

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2]])
    crawler._get_provider = lambda name: provider1 if name == "provider1" else provider2

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act & Assert: Raises RuntimeError after trying all candidates
    with pytest.raises(RuntimeError, match="Failed to download report.*after trying"):
        crawler.download_best_report(company, year=2023)


@pytest.mark.cp
def test_download_handles_provider_not_found():
    """Failure path: download_best_report() handles case where provider name doesn't match any provider."""
    # Arrange: SourceRef references non-existent provider
    provider1 = MagicMock()
    provider1.search.return_value = [
        SourceRef(provider="nonexistent_provider", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1")
    ]

    crawler = MultiSourceCrawler(tiers=[[provider1]])
    crawler._get_provider = lambda name: None  # Provider not found

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act & Assert: Should skip candidate and raise RuntimeError (no successful download)
    with pytest.raises(RuntimeError, match="Failed to download report"):
        crawler.download_best_report(company, year=2023)


@pytest.mark.cp
def test_search_handles_provider_without_enabled_attribute():
    """Failure path: search_company_reports() handles providers without 'enabled' attribute (defaults to True)."""
    # Arrange: Provider without 'enabled' attribute
    provider_no_attr = MagicMock(spec=[])  # spec=[] means no attributes
    provider_no_attr.search.return_value = [
        SourceRef(provider="provider_no_attr", tier=1, content_type="application/pdf", priority_score=10)
    ]

    crawler = MultiSourceCrawler(tiers=[[provider_no_attr]])
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    candidates = crawler.search_company_reports(company, year=2023)

    # Assert: Provider was called (defaults to enabled=True)
    assert provider_no_attr.search.called
    assert len(candidates) == 1


@pytest.mark.cp
def test_download_handles_rate_limit_error():
    """Failure path: download_best_report() handles RateLimitExceededError and falls back."""
    # Arrange: First provider rate limited, second succeeds
    provider1 = MagicMock()
    provider1.search.return_value = [
        SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1")
    ]
    provider1.download.side_effect = RateLimitExceededError("503 Rate Limit")

    provider2 = MagicMock()
    provider2.search.return_value = [
        SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20, url="http://example.com/2")
    ]
    provider2.download.return_value = CompanyReport(
        company=CompanyRef(cik="0000320193", name="Apple Inc."),
        year=2023,
        source=SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20),
        local_path="/tmp/report.html",
        sha256="abc123"
    )

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2]])
    crawler._get_provider = lambda name: provider1 if name == "provider1" else provider2

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    report = crawler.download_best_report(company, year=2023)

    # Assert: Fallback provider's report returned
    assert report.source.provider == "provider2"


@pytest.mark.cp
def test_download_handles_document_not_found_error():
    """Failure path: download_best_report() handles DocumentNotFoundError (404) and falls back."""
    # Arrange: First provider returns 404, second succeeds
    provider1 = MagicMock()
    provider1.search.return_value = [
        SourceRef(provider="provider1", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1")
    ]
    provider1.download.side_effect = DocumentNotFoundError("404 Not Found")

    provider2 = MagicMock()
    provider2.search.return_value = [
        SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20, url="http://example.com/2")
    ]
    provider2.download.return_value = CompanyReport(
        company=CompanyRef(cik="0000320193", name="Apple Inc."),
        year=2023,
        source=SourceRef(provider="provider2", tier=2, content_type="text/html", priority_score=20),
        local_path="/tmp/report.html",
        sha256="def456"
    )

    crawler = MultiSourceCrawler(tiers=[[provider1], [provider2]])
    crawler._get_provider = lambda name: provider1 if name == "provider1" else provider2

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    report = crawler.download_best_report(company, year=2023)

    # Assert: Fallback provider's report returned (404 didn't crash download)
    assert report.source.provider == "provider2"


# ============================================================================
# INTEGRATION TESTS (Real SEC EDGAR Provider - Phase 1 Compatibility)
# ============================================================================

@pytest.mark.integration
@pytest.mark.cp
def test_phase1_sec_edgar_provider_works_with_phase2_crawler():
    """Integration test: Phase 1 SEC EDGAR provider compatible with Phase 2 crawler."""
    # This test uses REAL SEC EDGAR provider from Phase 1
    # Marked @pytest.mark.integration - only runs when explicitly enabled

    from agents.crawler.data_providers.sec_edgar_provider import SECEdgarProvider

    # Arrange: Real SEC EDGAR provider
    sec_provider = SECEdgarProvider(contact_email="test@example.com")

    # Wrap in Phase 2 crawler
    crawler = MultiSourceCrawler(tiers=[[sec_provider]])

    # Search for Apple 2023 10-K
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    candidates = crawler.search_company_reports(company, year=2023)

    # Assert: Results returned
    assert len(candidates) > 0, "No candidates found from SEC EDGAR"

    # Assert: All SourceRef objects
    assert all(isinstance(c, SourceRef) for c in candidates), "Not all SourceRef"

    # Assert: All tier 1 (SEC EDGAR is Tier 1A)
    assert all(c.tier == 1 for c in candidates), "SEC EDGAR should be tier 1"

    # Assert: Provider name correct
    assert all(c.provider == "sec_edgar" for c in candidates), "Wrong provider name"


@pytest.mark.integration
@pytest.mark.cp
def test_multi_source_download_with_real_sec_edgar():
    """Integration test: Full download workflow with real SEC EDGAR provider."""
    # Marked @pytest.mark.integration - only runs when explicitly enabled

    from agents.crawler.data_providers.sec_edgar_provider import SECEdgarProvider

    # Arrange: Real SEC EDGAR provider + mock fallback provider
    sec_provider = SECEdgarProvider(contact_email="test@example.com")

    mock_provider = MagicMock()
    mock_provider.enabled = True
    mock_provider.search.return_value = [
        SourceRef(provider="mock_fallback", tier=2, content_type="text/html", priority_score=50)
    ]

    # Crawler with real provider as tier 1, mock as tier 2
    crawler = MultiSourceCrawler(tiers=[[sec_provider], [mock_provider]])

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    report = crawler.download_best_report(company, year=2023)

    # Assert: Downloaded from SEC EDGAR (tier 1, best priority)
    assert report.source.tier == 1
    assert report.source.provider == "sec_edgar"

    # Assert: Mock provider NOT called (SEC EDGAR succeeded)
    assert not mock_provider.download.called


# ============================================================================
# DIFFERENTIAL TESTS (Phase 1 Compatibility)
# ============================================================================

@pytest.mark.cp
def test_phase1_provider_output_parity():
    """Differential test: Phase 2 crawler returns same SourceRef structure as Phase 1."""
    # This test ensures Phase 2 doesn't break Phase 1 provider's output contract

    # Arrange: Mock Phase 1 provider that returns SourceRef results
    phase1_provider = MagicMock()
    phase1_provider.enabled = True
    phase1_provider.search.return_value = [
        SourceRef(
            provider="sec_edgar",
            tier=1,
            url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm",
            content_type="text/html",
            priority_score=20
        )
    ]

    crawler = MultiSourceCrawler(tiers=[[phase1_provider]])
    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act
    candidates = crawler.search_company_reports(company, year=2023)

    # Assert: SourceRef structure matches expectations
    assert len(candidates) == 1
    source_ref = candidates[0]

    assert source_ref.provider == "sec_edgar"
    assert source_ref.tier == 1
    assert source_ref.url is not None
    assert source_ref.content_type == "text/html"
    assert source_ref.priority_score == 20


# ============================================================================
# SENSITIVITY TESTS (Fallback Robustness)
# ============================================================================

@pytest.mark.cp
@pytest.mark.parametrize("num_failures", [0, 1, 2, 3, 4])
def test_fallback_handles_n_failures(num_failures):
    """Sensitivity test: Download fallback works when first N providers fail."""
    # Arrange: 5 mock providers
    providers = []
    for i in range(5):
        provider = MagicMock()
        provider.search.return_value = [
            SourceRef(provider=f"provider{i}", tier=i+1, content_type="application/pdf", priority_score=i*10, url=f"http://example.com/{i}")
        ]

        if i < num_failures:
            # First N providers fail
            provider.download.side_effect = RequestTimeoutError(f"Provider {i} timeout")
        else:
            # (N+1)th provider succeeds
            provider.download.return_value = CompanyReport(
                company=CompanyRef(cik="0000320193", name="Apple Inc."),
                year=2023,
                source=SourceRef(provider=f"provider{i}", tier=i+1, content_type="application/pdf", priority_score=i*10),
                local_path=f"/tmp/report{i}.pdf",
                sha256=f"hash{i}"
            )

        providers.append(provider)

    crawler = MultiSourceCrawler(tiers=[[p] for p in providers])
    crawler._get_provider = lambda name: next((p for p in providers if f"provider{providers.index(p)}" == name), None)

    company = CompanyRef(cik="0000320193", name="Apple Inc.")

    # Act & Assert
    if num_failures < 5:
        # Should succeed by falling back to (N+1)th provider
        report = crawler.download_best_report(company, year=2023)
        assert report.source.provider == f"provider{num_failures}"

        # Verify all providers up to (N+1) were tried
        for i in range(num_failures + 1):
            assert providers[i].download.called
    else:
        # All providers failed - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to download report"):
            crawler.download_best_report(company, year=2023)


@pytest.mark.cp
def test_prioritization_stable_with_tied_scores():
    """Sensitivity test: Prioritization is stable when multiple candidates have same tier and priority_score."""
    # Arrange: 3 candidates with identical tier and priority_score
    candidates = [
        SourceRef(provider="p1", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/1"),
        SourceRef(provider="p2", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/2"),
        SourceRef(provider="p3", tier=1, content_type="application/pdf", priority_score=10, url="http://example.com/3"),
    ]

    crawler = MultiSourceCrawler(tiers=[])

    # Act: Sort multiple times
    sorted1 = crawler._prioritize_candidates(candidates)
    sorted2 = crawler._prioritize_candidates(candidates)
    sorted3 = crawler._prioritize_candidates(candidates)

    # Assert: Stable sort (same order every time)
    assert sorted1 == sorted2 == sorted3

    # Assert: Original order preserved for ties (stable sort property)
    assert sorted1[0].provider == "p1"
    assert sorted1[1].provider == "p2"
    assert sorted1[2].provider == "p3"


# ============================================================================
# Test Summary
# ============================================================================
"""
Test Coverage Summary (Phase 2 - v3 Enhancement #1):

Unit Tests (10):
✅ test_search_company_reports_calls_all_enabled_providers
✅ test_search_skips_disabled_providers
✅ test_search_continues_on_provider_failure
✅ test_prioritize_candidates_sorts_by_tier_then_priority_score
✅ test_prioritize_handles_empty_list
✅ test_download_best_report_tries_candidates_in_priority_order
✅ test_download_falls_back_to_next_candidate_on_failure
✅ test_get_provider_returns_correct_provider_by_name
✅ test_search_validates_all_source_refs_are_valid
✅ test_download_best_report_returns_first_successful_download

Property Tests (3):
✅ test_prioritization_invariant_tier_ordering (Hypothesis)
✅ test_prioritization_is_deterministic (Hypothesis)
✅ test_source_ref_rejects_invalid_priority_score (Hypothesis)

Failure-Path Tests (6):
✅ test_download_raises_exception_when_no_candidates_found
✅ test_download_raises_exception_when_all_downloads_fail
✅ test_download_handles_provider_not_found
✅ test_search_handles_provider_without_enabled_attribute
✅ test_download_handles_rate_limit_error
✅ test_download_handles_document_not_found_error

Integration Tests (2):
✅ test_phase1_sec_edgar_provider_works_with_phase2_crawler
✅ test_multi_source_download_with_real_sec_edgar

Differential Tests (1):
✅ test_phase1_provider_output_parity

Sensitivity Tests (2):
✅ test_fallback_handles_n_failures (parameterized: 5 test cases)
✅ test_prioritization_stable_with_tied_scores

Total: 24 tests (29 including parameterized variants)

SCA v13.8 Compliance:
✅ All tests marked @pytest.mark.cp
✅ ≥3 Hypothesis property tests
✅ ≥6 failure-path tests
✅ Tests written BEFORE implementation (TDD)
✅ Coverage target: ≥95% on multi_source_crawler.py
✅ Differential tests ensure Phase 1 compatibility

Phase 2 Focus:
✅ Search ALL tiers comprehensively (test_search_company_reports_calls_all_enabled_providers)
✅ Prioritize by (tier, priority_score) (test_prioritize_candidates_sorts_by_tier_then_priority_score)
✅ Download with fallback (test_download_falls_back_to_next_candidate_on_failure)
✅ Fail-closed on total failure (test_download_raises_exception_when_all_downloads_fail)
"""
