import logging
from datetime import datetime

"""
SASB (Sustainability Accounting Standards Board) Navigator Provider

Provides industry-specific material ESG issues and disclosure guidance using SASB Standards.
SASB covers 77 industries across 11 sectors with 26 ESG issue categories.

Data Source: https://www.sasb.org/standards/
"""

import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import json

from agents.crawler.data_providers.base_provider import BaseDataProvider, CompanyReport


class SASBNavigatorProvider(BaseDataProvider):
    """
    SASB Standards Navigator provider for material ESG issues

    Tier 2 metadata provider that identifies material ESG issues by industry and provides
    guidance on where to find disclosures in SEC filings. Complements SEC EDGAR by
    highlighting ESG-specific sections within 10-K/20-F reports.

    Features:
    - Maps company → industry → material ESG issues
    - Provides disclosure topic guidance
    - Links to relevant SEC filing sections (Item 1A, Item 7, etc.)
    - Returns SASB standards documents

    NOTE: SASB provides *guidance* on material issues, not actual sustainability reports.
    Use in combination with SEC EDGAR or GRI Database for actual report content.
    """

    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize SASB Navigator provider

        Args:
            rate_limit: Minimum seconds between requests (default 1.0 = 1 req/sec)
        """
        super().__init__(source_id="sasb_navigator", rate_limit=rate_limit)
        self.base_url = "https://www.sasb.org"
        self.api_endpoint = f"{self.base_url}/api/standards"  # Hypothetical API endpoint

        # Static mapping of common companies to SASB industry codes
        # In production, this would be a database lookup or API call
        self._industry_mapping = self._load_industry_mapping()

    def _load_industry_mapping(self) -> Dict[str, str]:
        """
        Load or fetch company → industry code mapping

        Returns:
            Dict mapping company names to SASB industry codes
        """
        # Simplified static mapping for common companies
        # In production, this would query an API or database
        return {
            "apple": "TC-HW",  # Technology & Communications - Hardware
            "microsoft": "TC-SI",  # Software & IT Services
            "tesla": "TR-AU",  # Transportation - Automobiles
            "exxonmobil": "EM-EP",  # Energy - Oil & Gas Exploration & Production
            "exxon mobil": "EM-EP",
            "walmart": "CG-MR",  # Consumer Goods - Multiline & Specialty Retailers
            "jpmorgan chase": "FN-CB",  # Financials - Commercial Banks
            "jpmorgan": "FN-CB",
            "unilever": "CG-HP",  # Consumer Goods - Household & Personal Products
        }

    def _get_industry_code(self, company_name: str) -> Optional[str]:
        """
        Get SASB industry code for a company

        Args:
            company_name: Company name

        Returns:
            SASB industry code (e.g., "TC-HW") or None if not found
        """
        if not company_name:
            return None

        company_lower = company_name.lower().strip()

        # Try exact match first
        if company_lower in self._industry_mapping:
            return self._industry_mapping[company_lower]

        # Try partial match (e.g., "Apple Inc." matches "apple")
        for key, industry_code in self._industry_mapping.items():
            if key in company_lower or company_lower in key:
                return industry_code

        # Try API lookup if available
        try:
            response = requests.get(
                f"{self.api_endpoint}/company-industry",
                params={"q": company_name},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("industry_code")

        except Exception as e:
            logger.warning(f"SASB lookup failed: {e}")

        return None

    def search_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search for material ESG issues for a company using SASB Navigator

        Args:
            company_name: Company name
            company_id: SASB industry code (if known)
            year: Target year (metadata only, SASB standards stable across years)

        Returns:
            List with single CompanyReport containing material issues metadata
        """
        if not company_name and not company_id:
            return []

        self._enforce_rate_limit()

        try:
            # Get industry code
            industry_code = company_id if company_id else self._get_industry_code(company_name)

            if not industry_code:
                return []

            # Fetch material issues for industry
            material_issues = self._fetch_material_issues(industry_code)

            if not material_issues:
                return []

            # Fetch disclosure guidance (SEC filing sections where issues are typically disclosed)
            disclosure_guidance = self._fetch_disclosure_guidance(industry_code)

            # Create a single report representing SASB material issues for this company
            report = CompanyReport(
                company_name=company_name or industry_code,
                company_id=industry_code,
                year=year if year else datetime.now().year,
                report_type="sasb_material_issues",
                report_title=f"SASB Material ESG Issues for {company_name} ({industry_code})",
                download_url=material_issues.get("source_url"),
                file_format="pdf",  # SASB standards available as PDF
                file_size_bytes=None,
                source="sasb_navigator",
                source_metadata={
                    "industry_code": industry_code,
                    "industry_name": material_issues.get("industry_name"),
                    "sector": material_issues.get("sector"),
                    "material_issues": material_issues.get("material_issues", []),
                    "disclosure_guidance": disclosure_guidance,
                },
                date_published=None,  # SASB standards periodically updated
                date_retrieved=datetime.now().strftime("%Y-%m-%d"),
            )

            return [report]

        except requests.exceptions.Timeout:
            return []
        except requests.exceptions.ConnectionError:
            return []
        except Exception:
            return []

    def _fetch_material_issues(self, industry_code: str) -> Dict[str, Any]:
        """
        Fetch material ESG issues for a SASB industry

        Args:
            industry_code: SASB industry code (e.g., "TC-HW")

        Returns:
            Dict with material issues data
        """
        try:
            response = requests.get(
                f"{self.api_endpoint}/industries/{industry_code}",
                timeout=10
            )

            if response.status_code != 200:
                return {}

            data = response.json()
            return data

        except requests.exceptions.HTTPError:
            return {}
        except json.JSONDecodeError:
            return {}
        except Exception:
            return {}

    def _fetch_disclosure_guidance(self, industry_code: str) -> List[Dict[str, Any]]:
        """
        Fetch disclosure guidance for SASB industry

        Provides guidance on which SEC filing sections typically contain
        disclosures for each material issue.

        Args:
            industry_code: SASB industry code

        Returns:
            List of disclosure guidance items
        """
        try:
            response = requests.get(
                f"{self.api_endpoint}/disclosure-guidance/{industry_code}",
                timeout=10
            )

            if response.status_code != 200:
                return []

            data = response.json()
            return data.get("disclosure_guidance", [])

        except Exception:
            return []

    def download_report(
        self,
        report: CompanyReport,
        output_path: str
    ) -> bool:
        """
        Download SASB standards PDF for an industry

        Args:
            report: Report metadata from search_company()
            output_path: Local path to save file

        Returns:
            True if successful, False otherwise
        """
        if not report.download_url:
            return False

        self._enforce_rate_limit()

        try:
            response = requests.get(report.download_url, timeout=30)

            if response.status_code != 200:
                return False

            # Write to file
            with open(output_path, 'wb') as f:
                f.write(response.content)

            return True

        except requests.exceptions.HTTPError:
            return False
        except requests.exceptions.ConnectionError:
            return False
        except requests.exceptions.Timeout:
            return False
        except Exception:
            return False

    def list_available_companies(
        self,
        limit: int = 100
    ) -> List[Dict[str, str]]:
        """
        List available SASB industries (not companies)

        SASB organizes by industry, not individual companies. This returns
        the list of 77 industries covered by SASB Standards.

        Args:
            limit: Maximum number of industries to return

        Returns:
            List of dicts with 'company_name' (industry name) and 'company_id' (industry code)
        """
        self._enforce_rate_limit()

        try:
            response = requests.get(
                f"{self.api_endpoint}/industries",
                params={"limit": limit},
                timeout=10
            )

            if response.status_code != 200:
                return []

            data = response.json()

            industries = []
            for industry in data.get("industries", [])[:limit]:
                industries.append({
                    "company_name": f"{industry.get('industry_name', '')} ({industry.get('industry_code', '')})",
                    "company_id": industry.get("industry_code", ""),
                    "sector": industry.get("sector", ""),
                })

            return industries

        except requests.exceptions.HTTPError:
            return []
        except Exception:
            return []
