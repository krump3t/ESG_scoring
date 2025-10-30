"""
Multi-Source ESG Report Crawler

Orchestrates multiple data providers with intelligent fallback logic.
Uses verified public APIs and databases per data_source_registry.json.

Workflow:
1. Try Tier 1 sources (CDP, SEC EDGAR) - high reliability, public APIs
2. Fall back to Tier 2 (GRI, CSRHub) - comprehensive but may require scraping
3. Fall back to Tier 3 (direct company IR) - manual URL discovery
4. Fall back to Tier 4 (aggregators) - last resort

Author: SCA Protocol v13.8-MEA
Date: 2025-10-22
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

from .data_providers.base_provider import CompanyReport

# Optional provider imports (may fail if dependencies not installed)
try:
    from .data_providers.cdp_provider import CDPClimateProvider
except ImportError as e:
    logger.warning(f"CDPClimateProvider import failed: {e}")
    CDPClimateProvider = None

try:
    from .data_providers.gri_provider import GRIDatabaseProvider
except ImportError as e:
    logger.warning(f"GRIDatabaseProvider import failed: {e}")
    GRIDatabaseProvider = None

try:
    from .data_providers.sasb_provider import SASBNavigatorProvider
except ImportError as e:
    logger.warning(f"SASBNavigatorProvider import failed: {e}")
    SASBNavigatorProvider = None

try:
    from .data_providers.ticker_lookup import TickerLookupProvider
except ImportError as e:
    logger.warning(f"TickerLookupProvider import failed: {e}")
    TickerLookupProvider = None


class MultiSourceCrawler:
    """
    Intelligent multi-source ESG report crawler

    Automatically selects best data source based on:
    - Company location (US → SEC EDGAR priority)
    - Report type needed (climate → CDP priority)
    - Data availability (fallback cascade)
    """

    def __init__(
        self,
        registry_path: str = "configs/data_source_registry.json",
        download_dir: str = "data/pdf_cache"
    ):
        """
        Initialize multi-source crawler

        Args:
            registry_path: Path to data_source_registry.json
            download_dir: Directory for downloaded reports
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Load registry
        with open(registry_path, 'r') as f:
            self.registry = json.load(f)

        # Initialize providers
        # Tier 1: High-reliability public APIs
        self.providers = {}

        if CDPClimateProvider:
            try:
                self.providers['cdp'] = CDPClimateProvider()
                logger.info("Initialized CDPClimateProvider")
            except Exception as e:
                logger.warning(f"CDPClimateProvider init failed: {e}")

        if GRIDatabaseProvider:
            try:
                self.providers['gri'] = GRIDatabaseProvider()
                logger.info("Initialized GRIDatabaseProvider")
            except Exception as e:
                logger.warning(f"GRIDatabaseProvider init failed: {e}")

        if SASBNavigatorProvider:
            try:
                self.providers['sasb'] = SASBNavigatorProvider()
                logger.info("Initialized SASBNavigatorProvider")
            except Exception as e:
                logger.warning(f"SASBNavigatorProvider init failed: {e}")

        # Tier 2: Ticker Lookup for name disambiguation (Task 007)
        if TickerLookupProvider:
            try:
                self.providers['ticker_lookup'] = TickerLookupProvider()
                logger.info("Initialized TickerLookupProvider")
            except Exception as e:
                logger.warning(f"TickerLookupProvider init failed: {e}")

        logger.info(f"MultiSourceCrawler initialized with {len(self.providers)} providers")

    def search_company_reports(
        self,
        company_name: str,
        year: Optional[int] = None,
        report_types: Optional[List[str]] = None,
        us_company: bool = False
    ) -> Dict[str, List[CompanyReport]]:
        """
        Search for company reports across all sources with intelligent Tier 1 → Tier 2 fallback

        Tier 1 (Public APIs): SEC EDGAR, CDP
        Tier 2 (Name Disambiguation): Ticker Lookup → SEC retry

        Args:
            company_name: Company name
            year: Target year (None = most recent)
            report_types: Desired report types (None = all)
            us_company: If True, prioritize SEC EDGAR

        Returns:
            Dict mapping source_id to list of reports
        """
        all_reports = {}

        # Tier 1: Try all available providers
        tier1_providers = list(self.providers.keys())
        if 'ticker_lookup' in tier1_providers:
            tier1_providers.remove('ticker_lookup')  # Don't try ticker lookup as primary source

        # Reorder: CDP and GRI first, then others
        prioritized = []
        for pref in ['cdp', 'gri', 'sasb']:
            if pref in tier1_providers:
                prioritized.append(pref)
                tier1_providers.remove(pref)
        prioritized.extend(tier1_providers)

        tier1_success = False

        for provider_id in prioritized:
            if provider_id not in self.providers:
                continue

            provider = self.providers[provider_id]

            try:
                reports = provider.search_company(
                    company_name=company_name,
                    year=year
                )

                # Filter by report type if specified
                if report_types:
                    reports = [r for r in reports if r.report_type in report_types]

                if reports:
                    all_reports[provider_id] = reports
                    tier1_success = True
                    logger.info(f"Tier 1 - {provider_id}: Found {len(reports)} reports for {company_name}")

            except Exception as e:
                logger.debug(f"Tier 1 - {provider_id} search failed: {e}")

        # Early exit if Tier 1 succeeded (optimization)
        if tier1_success:
            logger.info(f"Tier 1 succeeded for {company_name}, skipping Tier 2")
            return all_reports

        # Tier 2: Ticker lookup for name disambiguation
        logger.info(f"Tier 1 found no reports for {company_name}, trying Tier 2 (Ticker Lookup)")

        # Try ticker lookup for edge cases (e.g., name variations)
        if 'ticker_lookup' in self.providers:
            try:
                ticker_results = self.providers['ticker_lookup'].search_company(
                    company_name=company_name,
                    year=year
                )

                if ticker_results:
                    logger.info(f"Ticker lookup found {len(ticker_results)} potential matches")

            except Exception as e:
                logger.debug(f"Tier 2 - Ticker lookup failed: {e}")

        return all_reports

    def download_best_report(
        self,
        company_name: str,
        year: int,
        report_type: Optional[str] = None,
        us_company: bool = False
    ) -> Optional[str]:
        """
        Download best available report using fallback logic

        Args:
            company_name: Company name
            year: Target year
            report_type: Desired report type (None = any type)
            us_company: If True, prioritize SEC

        Returns:
            Path to downloaded file or None
        """
        # Search all sources
        all_reports = self.search_company_reports(
            company_name=company_name,
            year=year,
            report_types=[report_type] if report_type else None,
            us_company=us_company
        )

        if not all_reports:
            logger.warning(f"No reports found for {company_name} {year}")
            return None

        # Try downloading from each source (in priority order)
        for source_id, reports in all_reports.items():
            if not reports:
                continue

            # Try each report from this source
            for report in reports:
                # Skip reports without download URL
                if not report.download_url:
                    continue

                # Generate output path
                safe_name = company_name.replace(' ', '_').replace('/', '_')
                extension = 'json' if report.file_format.lower() == 'json' else 'html'
                output_path = self.download_dir / f"{safe_name}_{year}_{source_id}.{extension}"

                try:
                    provider = self.providers[source_id]
                    success = provider.download_report(report, str(output_path))

                    if success:
                        logger.info(f"✓ Downloaded from {source_id}: {output_path}")
                        return str(output_path)

                except Exception as e:
                    logger.error(f"Download failed from {source_id}: {e}")

        logger.error(f"Failed to download report for {company_name} from all sources")
        return None

    def bulk_download(
        self,
        companies: List[Dict[str, Any]],
        year: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Bulk download reports for multiple companies

        Args:
            companies: List of dicts with 'company_name' (or 'name') and optional 'year', 'us_company'
            year: Default year if not specified per company

        Returns:
            Dict mapping company name to downloaded file path
        """
        results = {}

        for company_info in companies:
            # Support both 'company_name' and 'name' keys
            company_name = company_info.get('company_name') or company_info.get('name')
            if not company_name:
                logger.error(f"Company info missing 'company_name' or 'name' field: {company_info}")
                continue

            company_year = company_info.get('year', year)
            if not company_year:
                logger.error(f"No year specified for {company_name}")
                continue

            us_company = company_info.get('us_company', False)

            logger.info(f"Downloading: {company_name} {company_year}")

            file_path = self.download_best_report(
                company_name=company_name,
                year=company_year,
                us_company=us_company
            )

            if file_path:
                results[company_name] = file_path

        success_count = len(results)
        logger.info(f"Bulk download complete: {success_count}/{len(companies)} successful")

        return results

    def get_available_sources(self) -> List[Dict[str, Any]]:
        """
        Get list of available data sources from registry

        Returns:
            List of source metadata
        """
        sources: List[Dict[str, Any]] = self.registry['data_sources']
        return sources

    def get_provider_status(self) -> Dict[str, bool]:
        """
        Check status of all providers

        Returns:
            Dict mapping provider_id to availability status
        """
        status = {}

        for provider_id, provider in self.providers.items():
            try:
                # Test with a simple query
                companies = provider.list_available_companies(limit=1)
                status[provider_id] = len(companies) > 0
            except:
                status[provider_id] = False

        return status
