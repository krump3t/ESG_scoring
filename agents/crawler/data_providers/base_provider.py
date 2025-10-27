"""
Base class for data providers

All data providers must implement this interface for consistency.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from libs.utils.clock import get_clock
clock = get_clock()


@dataclass
class CompanyReport:
    """Standardized company report metadata"""
    company_name: str
    company_id: Optional[str]  # Ticker, CIK, or provider-specific ID
    year: int
    report_type: str  # "sustainability", "climate", "10-k", "esg"
    report_title: str
    download_url: Optional[str]
    file_format: str  # "PDF", "JSON", "HTML", "XML"
    file_size_bytes: Optional[int]
    source: str  # Provider ID (e.g., "cdp_climate_change")
    source_metadata: Dict[str, Any]  # Provider-specific metadata
    date_published: Optional[str]
    date_retrieved: str


class BaseDataProvider(ABC):
    """
    Base class for all data providers

    Providers must implement:
    - search_company(): Find reports for a company
    - download_report(): Download a specific report
    - list_available_companies(): Get list of companies with data
    """

    def __init__(self, source_id: str, rate_limit: float = 1.0):
        """
        Initialize provider

        Args:
            source_id: ID from data_source_registry.json
            rate_limit: Minimum seconds between requests
        """
        self.source_id = source_id
        self.rate_limit = rate_limit
        self._last_request_time = 0.0

    @abstractmethod
    def search_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search for company reports

        Args:
            company_name: Company name (fuzzy match supported)
            company_id: Company identifier (ticker, CIK, etc.)
            year: Target year (None = all years)

        Returns:
            List of available reports
        """
        pass

    @abstractmethod
    def download_report(
        self,
        report: CompanyReport,
        output_path: str
    ) -> bool:
        """
        Download a specific report

        Args:
            report: Report metadata from search_company()
            output_path: Local path to save file

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def list_available_companies(
        self,
        limit: int = 100
    ) -> List[Dict[str, str]]:
        """
        List companies with available data

        Args:
            limit: Maximum number of companies to return

        Returns:
            List of dicts with 'company_name' and 'company_id'
        """
        pass

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
        import time
        elapsed = clock.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time = clock.time()
