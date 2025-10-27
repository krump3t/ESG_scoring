"""
GRI (Global Reporting Initiative) Database Provider

Provides access to sustainability reports from the GRI Sustainability Disclosure Database.
GRI Standards are the most widely used ESG reporting framework globally, with 13,000+
organizations in 100+ countries.

Data Source: https://database.globalreporting.org/
"""

import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import json
from bs4 import BeautifulSoup

from agents.crawler.data_providers.base_provider import BaseDataProvider, CompanyReport


class GRIDatabaseProvider(BaseDataProvider):
    """
    GRI Database provider for sustainability reports

    Tier 2 provider that searches the GRI Sustainability Disclosure Database for company
    sustainability reports. Fills gaps in Tier 1 (SEC EDGAR) for:
    - International companies (non-US)
    - Non-public companies (private, non-profits)
    - Voluntary ESG reporters

    Features:
    - Search by company name (fuzzy matching supported)
    - Filter by year
    - Returns report metadata with download links
    - Rate limiting (1 req/sec default)
    """

    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize GRI Database provider

        Args:
            rate_limit: Minimum seconds between requests (default 1.0 = 1 req/sec)
        """
        super().__init__(source_id="gri_database", rate_limit=rate_limit)
        self.base_url = "https://database.globalreporting.org"
        self.api_endpoint = f"{self.base_url}/api/search"  # Hypothetical API endpoint

    def search_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search for company sustainability reports in GRI Database

        Args:
            company_name: Company name (fuzzy match supported)
            company_id: GRI organization ID (if known)
            year: Target year (None = all years)

        Returns:
            List of available sustainability reports
        """
        if not company_name and not company_id:
            return []

        self._enforce_rate_limit()

        try:
            # Try API first (if available)
            results = self._search_via_api(company_name, company_id, year)
            if results:
                return results

            # Fallback to HTML parsing if API not available
            return self._search_via_html(company_name, year)

        except requests.exceptions.Timeout:
            return []
        except requests.exceptions.ConnectionError:
            return []
        except Exception as e:
            # Log error but return empty list instead of crashing
            return []

    def _search_via_api(
        self,
        company_name: Optional[str],
        company_id: Optional[str],
        year: Optional[int]
    ) -> List[CompanyReport]:
        """
        Search GRI database via API (if available)

        Returns:
            List of CompanyReport objects, or empty list if API unavailable
        """
        params: Dict[str, Any] = {}
        if company_name:
            params["q"] = company_name
        if company_id:
            params["org_id"] = company_id
        if year:
            params["year"] = year

        try:
            response = requests.get(
                self.api_endpoint,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                return []

            data = response.json()

            if "results" not in data:
                return []

            reports = []
            for result in data.get("results", []):
                # Skip if missing required fields
                if not all(k in result for k in ["organization_name", "report_year"]):
                    continue

                # Filter by year if specified
                report_year = result.get("report_year")
                if year and report_year != year:
                    continue

                report = CompanyReport(
                    company_name=result.get("organization_name", ""),
                    company_id=result.get("organization_id"),
                    year=report_year,
                    report_type="sustainability",
                    report_title=result.get("report_title", f"{result.get('organization_name')} Sustainability Report {report_year}"),
                    download_url=result.get("report_url"),
                    file_format="pdf",  # GRI reports are typically PDF
                    file_size_bytes=result.get("file_size"),
                    source="gri_database",
                    source_metadata={
                        "gri_standards_version": result.get("gri_standards_version"),
                        "country": result.get("country"),
                        "sector": result.get("sector"),
                        "publication_date": result.get("publication_date"),
                    },
                    date_published=result.get("publication_date"),
                    date_retrieved=datetime.now().strftime("%Y-%m-%d"),
                )
                reports.append(report)

            return reports

        except requests.exceptions.HTTPError:
            return []
        except json.JSONDecodeError:
            # API returned invalid JSON, fallback to HTML parsing
            return []

    def _search_via_html(
        self,
        company_name: Optional[str],
        year: Optional[int]
    ) -> List[CompanyReport]:
        """
        Fallback: Search GRI database via HTML parsing

        This is used when the API is not available or returns errors.

        Returns:
            List of CompanyReport objects
        """
        if not company_name:
            return []

        try:
            # Construct search URL (hypothetical based on typical search patterns)
            search_url = f"{self.base_url}/search"
            params = {"q": company_name}
            if year:
                params["year"] = year

            response = requests.get(search_url, params=params, timeout=10)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse HTML to extract report information
            # NOTE: This is a simplified example. Real implementation would need
            # to match the actual HTML structure of database.globalreporting.org
            reports = []

            # Example: Find all report items (adjust selectors to match actual HTML)
            for item in soup.find_all('div', class_='report-item'):
                org_name = item.find('h3', class_='organization-name')
                report_link = item.find('a', class_='report-title')
                report_year_elem = item.find('span', class_='report-year')

                if not all([org_name, report_link, report_year_elem]):
                    continue

                try:
                    report_year = int(report_year_elem.text.strip())
                except (ValueError, AttributeError):
                    continue

                # Filter by company name (case-insensitive fuzzy match)
                if company_name.lower() not in org_name.text.lower():
                    continue

                # Filter by year if specified
                if year and report_year != year:
                    continue

                report_url = report_link.get('href', '')
                if not report_url.startswith('http'):
                    report_url = f"{self.base_url}{report_url}"

                report = CompanyReport(
                    company_name=org_name.text.strip(),
                    company_id=None,
                    year=report_year,
                    report_type="sustainability",
                    report_title=report_link.text.strip(),
                    download_url=report_url,
                    file_format="pdf",
                    file_size_bytes=None,
                    source="gri_database",
                    source_metadata={
                        "country": item.find('span', class_='country').text.strip() if item.find('span', class_='country') else None,
                        "sector": item.find('span', class_='sector').text.strip() if item.find('span', class_='sector') else None,
                    },
                    date_published=None,
                    date_retrieved=datetime.now().strftime("%Y-%m-%d"),
                )
                reports.append(report)

            return reports

        except requests.exceptions.HTTPError:
            return []
        except Exception:
            return []

    def download_report(
        self,
        report: CompanyReport,
        output_path: str
    ) -> bool:
        """
        Download a sustainability report from GRI Database

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
        List companies with available sustainability reports in GRI Database

        Args:
            limit: Maximum number of companies to return

        Returns:
            List of dicts with 'company_name' and 'company_id'
        """
        self._enforce_rate_limit()

        try:
            # Try API first
            response = requests.get(
                f"{self.base_url}/api/organizations",
                params={"limit": limit},
                timeout=10
            )

            if response.status_code != 200:
                return []

            data = response.json()

            companies = []
            for org in data.get("companies", [])[:limit]:
                companies.append({
                    "company_name": org.get("organization_name", ""),
                    "company_id": org.get("organization_id", ""),
                })

            return companies

        except requests.exceptions.HTTPError:
            return []
        except Exception:
            return []
