"""
CrawlerAdapter: Bridge between PipelineOrchestrator and MultiSourceCrawler APIs

Protocol: SCA v13.8-MEA
Task: 011-service-activation
"""

import logging
import json
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from agents.crawler.multi_source_crawler import MultiSourceCrawler

logger = logging.getLogger(__name__)


class CrawlerAdapter:
    """
    Adapter pattern implementation to bridge incompatible APIs.

    PipelineOrchestrator expects:
        crawler.crawl_company(company_cik: str, fiscal_year: int) -> dict

    MultiSourceCrawler provides:
        crawler.search_company_reports(company_name: str, year: int) -> dict[str, list[CompanyReport]]

    This adapter translates between the two interfaces.
    """

    def __init__(
        self,
        crawler: MultiSourceCrawler,
        cik_lookup: Optional[Callable[[str], Optional[str]]] = None
    ):
        """
        Initialize adapter with wrapped crawler instance.

        Args:
            crawler: MultiSourceCrawler instance to wrap
            cik_lookup: Optional callable that maps CIK → company name.
                        If None, uses default SEC dataset lookup.
        """
        self._crawler = crawler
        self._cik_lookup_fn = cik_lookup or self._load_default_cik_lookup()

    def _load_default_cik_lookup(self) -> Callable[[str], Optional[str]]:
        """
        Load default CIK → company name mapping from SEC dataset.

        Returns:
            Callable that maps CIK string to company name
        """
        try:
            # Try to load from common data paths
            data_paths = [
                Path(__file__).parents[2] / "tasks" / "007-tier2-data-providers" / "data" / "company_tickers.json",
                Path(__file__).parents[1] / "data" / "company_tickers.json",
                Path("data/company_tickers.json")
            ]

            company_data = {}
            for path in data_paths:
                if path.exists():
                    with open(path) as f:
                        company_data = json.load(f)
                    break

            if not company_data:
                logger.warning("SEC company_tickers.json not found, CIK lookup will fail")
                return lambda cik: None

            # Build reverse mapping: CIK → company name
            cik_to_name = {}
            for entry in company_data.values():
                cik_str = str(entry.get("cik_str", "")).zfill(10)  # Normalize CIK format
                company_name = entry.get("title", "")
                if cik_str and company_name:
                    cik_to_name[cik_str] = company_name

            logger.info(f"Loaded {len(cik_to_name)} companies from SEC dataset")

            return lambda cik: cik_to_name.get(cik.zfill(10))  # Normalize input CIK

        except Exception as e:
            logger.error(f"Failed to load SEC dataset: {e}")
            return lambda cik: None

    def crawl_company(self, company_cik: str, fiscal_year: int) -> dict:
        """
        Fetch company reports using CIK-based interface.

        Translates CIK → company name, then delegates to MultiSourceCrawler.

        Args:
            company_cik: SEC CIK number (e.g., "0000320193" for Apple)
            fiscal_year: Fiscal year (e.g., 2024)

        Returns:
            dict: {
                "sec_edgar": [CompanyReport, ...],
                "gri": [...],
                ...
            }
            Empty dict {} if CIK not found or crawler fails.

        Example:
            >>> adapter = CrawlerAdapter(MultiSourceCrawler())
            >>> result = adapter.crawl_company("0000320193", 2024)
            >>> print(result["sec_edgar"])
            [CompanyReport(...)]
        """
        # Step 1: Translate CIK to company name
        company_name = self._cik_to_company_name(company_cik)

        if company_name is None:
            logger.warning(f"CIK not found: {company_cik}")
            return {}

        # Step 2: Call MultiSourceCrawler with translated parameters
        try:
            result = self._crawler.search_company_reports(
                company_name=company_name,
                year=fiscal_year
            )
            return result

        except Exception as e:
            logger.error(f"Crawler failed for {company_name} ({company_cik}): {e}")
            return {}  # Graceful degradation

    def _cik_to_company_name(self, cik: str) -> Optional[str]:
        """
        Translate SEC CIK number to company name.

        Uses injected CIK lookup function (or default SEC dataset).

        Args:
            cik: SEC CIK number (e.g., "0000320193")

        Returns:
            Company name (e.g., "Apple Inc") or None if not found

        Example:
            >>> adapter._cik_to_company_name("0000320193")
            "Apple Inc"
        """
        try:
            company_name = self._cik_lookup_fn(cik)
            return company_name

        except Exception as e:
            logger.warning(f"CIK lookup failed for {cik}: {e}")
            return None
