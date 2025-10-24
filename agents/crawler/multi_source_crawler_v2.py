"""
Multi-Source Crawler v2 - Phase 2 (v3 Enhancement #1: Priority-Based Download)

**IMPORTANT**: This is the Phase 2 implementation based on TDD tests in:
- tests/crawler/test_multi_source_crawler_phase2.py (24 tests)
- Git commit c94f53b (tests before implementation)

**SCA v13.8 Compliance**:
- Implemented AFTER TDD tests
- 24 tests drive this implementation
- ≥95% coverage target
- Production-grade error handling

**v3 Enhancement #1**: Priority-Based Multi-Source Download
- Search ALL tiers comprehensively (not sequential fallback)
- Prioritize candidates by (tier, priority_score)
- Download best candidate with fallback on failure
- Fail-closed: raise exception if all downloads fail

**Architecture**:
1. search_company_reports() → List[SourceRef] (comprehensive search across all tiers)
2. _prioritize_candidates() → List[SourceRef] (sort by tier, priority_score)
3. download_best_report() → CompanyReport (download with fallback)

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24
"""

import logging
from typing import List, Optional
from libs.contracts.ingestion_contracts import CompanyRef, SourceRef, CompanyReport

logger = logging.getLogger(__name__)


class MultiSourceCrawler:
    """Multi-source crawler with priority-based download logic.

    **Phase 2 Focus**: Orchestration logic for v3 enhancement #1.

    Example Usage:
        >>> from agents.crawler.data_providers.sec_edgar_provider import SECEdgarProvider
        >>> sec_provider = SECEdgarProvider(contact_email="test@example.com")
        >>> crawler = MultiSourceCrawler(tiers=[[sec_provider]])
        >>>
        >>> company = CompanyRef(cik="0000320193", name="Apple Inc.")
        >>> report = crawler.download_best_report(company, year=2023)
        >>> print(f"Downloaded from {report.source.provider} (tier {report.source.tier})")
    """

    def __init__(self, tiers: List[List]):
        """Initialize multi-source crawler.

        Args:
            tiers: List of provider tiers (e.g., [[tier1_providers], [tier2_providers], [tier3_providers]])

        Example:
            >>> crawler = MultiSourceCrawler(tiers=[
            ...     [sec_edgar_provider, cdp_provider],  # Tier 1 (APIs)
            ...     [gri_provider],                       # Tier 2 (Databases)
            ...     [company_ir_provider]                 # Tier 3 (Web Scraping)
            ... ])
        """
        self.tiers = tiers
        logger.info(f"Initialized MultiSourceCrawler with {len(tiers)} tiers")

    # ========================================================================
    # PHASE 1: SEARCH (Comprehensive)
    # ========================================================================

    def search_company_reports(self, company: CompanyRef, year: int) -> List[SourceRef]:
        """Search ALL enabled providers across ALL tiers, return complete candidate list.

        **v3 Enhancement**: Searches ALL tiers before prioritization (not sequential fallback).
        This prevents missing high-value Tier 3 PDFs when low-value Tier 1 HTML exists.

        Args:
            company: Company reference (CIK, name, ticker)
            year: Fiscal year

        Returns:
            List of SourceRef objects from ALL enabled providers

        Raises:
            None - Fail-open (if one provider fails, continue with others)

        Example:
            >>> company = CompanyRef(cik="0000320193", name="Apple Inc.")
            >>> candidates = crawler.search_company_reports(company, year=2023)
            >>> print(f"Found {len(candidates)} candidates across all tiers")
        """
        all_candidates: List[SourceRef] = []

        logger.info(f"Searching for {company.name} ({year}) across {len(self.tiers)} tiers")

        for tier_index, providers in enumerate(self.tiers):
            tier_number = tier_index + 1

            for provider in providers:
                # Check if provider is enabled (defaults to True if attribute doesn't exist)
                if not getattr(provider, "enabled", True):
                    logger.info(f"Skipping disabled provider: {provider.__class__.__name__}")
                    continue

                try:
                    # Call provider's search method
                    tier_candidates = provider.search(company, year, tier=tier_number)

                    # Validate all SourceRef objects
                    valid_candidates = []
                    for candidate in tier_candidates:
                        if not isinstance(candidate, SourceRef):
                            logger.warning(
                                f"Provider {provider.__class__.__name__} returned non-SourceRef object: {type(candidate)}. Skipping."
                            )
                            continue

                        valid_candidates.append(candidate)

                    all_candidates.extend(valid_candidates)

                    logger.info(
                        f"Provider {provider.__class__.__name__} (tier {tier_number}) found {len(valid_candidates)} candidates"
                    )

                except Exception as e:
                    # Fail-open: log warning and continue to next provider
                    logger.warning(
                        f"Provider {provider.__class__.__name__} search failed: {e}. Continuing to next provider."
                    )
                    continue

        logger.info(f"Total candidates found: {len(all_candidates)} across {len(self.tiers)} tiers")
        return all_candidates

    # ========================================================================
    # PHASE 2: PRIORITIZE (Sorting)
    # ========================================================================

    def _prioritize_candidates(self, candidates: List[SourceRef]) -> List[SourceRef]:
        """Sort candidates by (tier, priority_score) ascending.

        **Algorithm**: Python's stable sort (Timsort) - O(n log n)
        - Lower tier = higher quality (1 > 2 > 3)
        - Lower priority_score = higher priority within tier (0 > 50 > 100)

        Args:
            candidates: Unsorted list of SourceRef objects

        Returns:
            Sorted list of SourceRef objects (best candidate first)

        Example:
            >>> candidates = [
            ...     SourceRef(provider="gri", tier=2, priority_score=30),
            ...     SourceRef(provider="sec", tier=1, priority_score=10),
            ... ]
            >>> sorted_candidates = crawler._prioritize_candidates(candidates)
            >>> assert sorted_candidates[0].provider == "sec"  # tier 1 before tier 2
        """
        if not candidates:
            logger.debug("No candidates to prioritize (empty list)")
            return []

        # Stable sort: preserves order for equal elements
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (c.tier, c.priority_score)
        )

        # Log top 5 candidates for debugging
        logger.debug(f"Prioritized {len(sorted_candidates)} candidates:")
        for i, candidate in enumerate(sorted_candidates[:5]):
            logger.debug(
                f"  {i+1}. {candidate.provider} (tier={candidate.tier}, priority={candidate.priority_score})"
            )

        return sorted_candidates

    # ========================================================================
    # PHASE 3: DOWNLOAD (Fallback)
    # ========================================================================

    def download_best_report(self, company: CompanyRef, year: int) -> CompanyReport:
        """Download best report with fallback to next candidate on failure.

        **v3 Enhancement**: Tries ALL candidates in priority order until one succeeds.
        Fail-closed: raises exception if ALL downloads fail (honest reporting).

        Workflow:
        1. Search all tiers → List[SourceRef]
        2. Prioritize candidates → sorted List[SourceRef]
        3. Try download from best candidate first
        4. If fails, try next candidate (fallback)
        5. If all fail, raise RuntimeError

        Args:
            company: Company reference
            year: Fiscal year

        Returns:
            CompanyReport from first successful download

        Raises:
            RuntimeError: If no candidates found or all downloads fail

        Example:
            >>> company = CompanyRef(cik="0000320193", name="Apple Inc.")
            >>> report = crawler.download_best_report(company, year=2023)
            >>> print(f"Downloaded {report.local_path} from {report.source.provider}")
        """
        # Step 1: Search all tiers
        all_candidates = self.search_company_reports(company, year)

        if not all_candidates:
            total_providers = sum(len(tier) for tier in self.tiers)
            raise RuntimeError(
                f"No report candidates found for {company.name} ({year}). "
                f"Searched {total_providers} providers across {len(self.tiers)} tiers."
            )

        # Step 2: Prioritize candidates
        sorted_candidates = self._prioritize_candidates(all_candidates)

        logger.info(
            f"Attempting download for {company.name} ({year}). "
            f"Trying {len(sorted_candidates)} candidates in priority order."
        )

        # Step 3: Try download from best candidate first, fallback on failure
        last_exception = None

        for i, source_ref in enumerate(sorted_candidates):
            try:
                # Get provider instance by name
                provider = self._get_provider(source_ref.provider)

                if not provider:
                    logger.warning(
                        f"Provider {source_ref.provider} not found in tiers. Skipping candidate {i+1}."
                    )
                    continue

                logger.info(
                    f"Attempting download (rank {i+1}/{len(sorted_candidates)}): "
                    f"{source_ref.provider} (tier={source_ref.tier}, priority={source_ref.priority_score})"
                )

                # Call provider's download method
                report = provider.download(source_ref, company, year)

                logger.info(
                    f"Successfully downloaded report from {source_ref.provider} "
                    f"(rank {i+1}/{len(sorted_candidates)})"
                )

                return report

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Download failed from {source_ref.provider} (rank {i+1}): {e}. "
                    f"Trying next candidate..."
                )
                # Continue to next candidate

        # All downloads failed - raise exception (fail-closed)
        raise RuntimeError(
            f"Failed to download report for {company.name} ({year}) after trying "
            f"{len(sorted_candidates)} candidates. Last error: {last_exception}"
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_provider(self, provider_name: str):
        """Get provider instance by name.

        Args:
            provider_name: Provider class name or identifier

        Returns:
            Provider instance if found, None otherwise

        Example:
            >>> provider = crawler._get_provider("SECEdgarProvider")
            >>> assert provider is not None
        """
        for tier in self.tiers:
            for provider in tier:
                # Match by class name or provider attribute
                if provider.__class__.__name__ == provider_name:
                    return provider

                # Also check for provider.name attribute if exists
                if hasattr(provider, "name") and provider.name == provider_name:
                    return provider

        logger.debug(f"Provider {provider_name} not found in any tier")
        return None


# ============================================================================
# USAGE EXAMPLE
# ============================================================================
"""
Example: Multi-source download with SEC EDGAR (Tier 1) + GRI (Tier 2) + Company IR (Tier 3)

```python
from agents.crawler.multi_source_crawler_v2 import MultiSourceCrawler
from agents.crawler.data_providers.sec_edgar_provider import SECEdgarProvider
from libs.contracts.ingestion_contracts import CompanyRef

# Initialize providers
sec_provider = SECEdgarProvider(contact_email="your.email@example.com")
# gri_provider = GRIProvider()  # Phase 2b
# company_ir_provider = CompanyIRProvider()  # Phase 2b

# Create crawler with tiered providers
crawler = MultiSourceCrawler(tiers=[
    [sec_provider],           # Tier 1 (APIs)
    # [gri_provider],         # Tier 2 (Databases) - Phase 2b
    # [company_ir_provider]   # Tier 3 (Web Scraping) - Phase 2b
])

# Search for reports
company = CompanyRef(cik="0000320193", name="Apple Inc.")
candidates = crawler.search_company_reports(company, year=2023)

print(f"Found {len(candidates)} candidates:")
for candidate in crawler._prioritize_candidates(candidates)[:3]:
    print(f"  - {candidate.provider} (tier={candidate.tier}, priority={candidate.priority_score})")

# Download best report
report = crawler.download_best_report(company, year=2023)
print(f"\nDownloaded from {report.source.provider}:")
print(f"  Local path: {report.local_path}")
print(f"  SHA256: {report.sha256}")
```

Output:
```
Found 3 candidates:
  - sec_edgar (tier=1, priority=5)   # XBRL JSON (best)
  - sec_edgar (tier=1, priority=10)  # 10-K PDF
  - sec_edgar (tier=1, priority=20)  # 10-K HTML

Downloaded from sec_edgar:
  Local path: /tmp/apple_10k_2023.json
  SHA256: abc123...
```
"""
