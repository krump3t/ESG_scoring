"""
CDP (Carbon Disclosure Project) Climate Change Data Provider

**LIMITATION DISCOVERED (2025-10-22):**
CDP Open Data Portal (data.cdp.net) contains Cities/States/Regions data, NOT corporate
company disclosures. Corporate CDP data requires paid access or CDP membership.

API Endpoint: https://data.cdp.net/api/odata/v4
Status: DISABLED for Task 006 (municipal data not relevant for corporate ESG)

For corporate CDP data access, see:
- https://www.cdp.net/en/data (requires CDP membership)
- Alternative: Use SEC EDGAR for US companies, direct report downloads for ESG data

**Original Intent (not achievable with free API):**
- Quantitative GHG emissions data (Scope 1, 2, 3)
- Climate targets and progress
- Risk/opportunity assessments
- Governance structures
- Standardized questionnaire responses
"""

import logging
import requests  # @allow-network:Crawler agent requires external API access to CDP Open Data Portal
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_provider import BaseDataProvider, CompanyReport
from libs.utils.clock import get_clock
clock = get_clock()

logger = logging.getLogger(__name__)


class CDPClimateProvider(BaseDataProvider):
    """
    CDP Climate Change data provider

    Uses CDP Open Data Portal OData v4 API
    """

    def __init__(self, rate_limit: float = 0.1):
        """
        Initialize CDP provider

        Args:
            rate_limit: Seconds between requests (CDP allows 10/sec)
        """
        super().__init__(source_id="cdp_climate_change", rate_limit=rate_limit)

        self.base_url = "https://data.cdp.net"
        self.api_endpoint = f"{self.base_url}/api/odata/v4"

        # CDP datasets (as of 2024)
        self.datasets = {
            "climate_change": "Climate Change",
            "water_security": "Water Security",
            "forests": "Forests"
        }

    def search_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search CDP data for company climate disclosures

        Args:
            company_name: Company name (fuzzy match)
            company_id: CDP account ID
            year: Target year (None = most recent)

        Returns:
            List of CompanyReport objects
        """
        self._enforce_rate_limit()

        reports = []

        try:
            # Use OData v4 API endpoint
            url = f"{self.api_endpoint}/ClimateChange"

            # Build OData filter
            filters = []
            if company_name:
                filters.append(f"contains(tolower(account_name), '{company_name.lower()}')")
            if company_id:
                filters.append(f"account_id eq '{company_id}'")
            if year:
                filters.append(f"year eq {year}")

            params = {}
            if filters:
                params['$filter'] = ' and '.join(filters)

            response = requests.get(
                url,
                params=params,
                timeout=30,
                headers={'User-Agent': 'ESG-Crawler/1.0 (Research)'}
            )

            if response.status_code == 200:
                data = response.json()

                # OData v4 returns results in 'value' array
                for result in data.get('value', []):
                    company_name_val = result.get('account_name', company_name)
                    year_val = result.get('year') or result.get('reporting_year', year or clock.now().year)

                    report = CompanyReport(
                        company_name=company_name_val,
                        company_id=str(result.get('account_id', '')),
                        year=year_val,
                        report_type='CDP Climate Response',
                        report_title=f"{company_name_val} {year_val} CDP Climate Response",
                        download_url=result.get('public_disclosure_url'),
                        file_format='json',
                        file_size_bytes=None,
                        source='cdp_climate_change',
                        source_metadata={
                            'account_id': result.get('account_id'),
                            'reporting_year': result.get('reporting_year'),
                            'ghg_scope1': result.get('ghg_scope1_tonnes_co2e'),
                            'ghg_scope2': result.get('ghg_scope2_tonnes_co2e'),
                            'ghg_scope3': result.get('ghg_scope3_tonnes_co2e'),
                        },
                        date_published=result.get('submission_date'),
                        date_retrieved=datetime.utcnow().strftime("%Y-%m-%d")
                    )
                    reports.append(report)

            logger.info(f"CDP search for '{company_name}': found {len(reports)} reports")

        except Exception as e:
            logger.error(f"CDP search failed: {e}")

        return reports

    def download_report(
        self,
        report: CompanyReport,
        output_path: str
    ) -> bool:
        """
        Download CDP climate response data

        Args:
            report: CompanyReport from search_company()
            output_path: Local file path to save JSON data

        Returns:
            True if successful
        """
        self._enforce_rate_limit()

        if not report.download_url:
            logger.warning(f"No download URL for {report.company_name}")
            return False

        try:
            response = requests.get(
                report.download_url,
                timeout=60,
                headers={'User-Agent': 'ESG-Crawler/1.0 (Research)'}
            )
            response.raise_for_status()

            # Save JSON data
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                # If response is JSON, pretty-print it
                try:
                    json_data = response.json()
                    json.dump(json_data, f, indent=2)
                except:
                    # Fallback to raw text
                    f.write(response.text)

            logger.info(f"Downloaded CDP data: {report.company_name} {report.year}")
            return True

        except Exception as e:
            logger.error(f"Failed to download CDP report: {e}")
            return False

    def list_available_companies(
        self,
        limit: int = 100
    ) -> List[Dict[str, str]]:
        """
        List companies with CDP climate data

        Args:
            limit: Maximum companies to return

        Returns:
            List of dicts with 'company_name' and 'company_id'
        """
        self._enforce_rate_limit()

        companies = []

        try:
            # Use OData v4 API to list companies
            url = f"{self.api_endpoint}/ClimateChange"
            params: Dict[str, Any] = {
                '$top': limit,
                '$select': 'account_name,account_id',
                '$orderby': 'account_name'
            }

            response = requests.get(
                url,
                params=params,
                timeout=30,
                headers={'User-Agent': 'ESG-Crawler/1.0 (Research)'}
            )

            if response.status_code == 200:
                data = response.json()
                # OData v4 returns results in 'value' array
                for company in data.get('value', []):
                    companies.append({
                        'company_name': company.get('account_name'),
                        'company_id': str(company.get('account_id', ''))
                    })

                # Apply limit client-side if API returned more
                companies = companies[:limit]

            logger.info(f"Listed {len(companies)} CDP companies")

        except Exception as e:
            logger.error(f"Failed to list CDP companies: {e}")

        return companies

    def get_company_ghg_emissions(
        self,
        company_name: str,
        year: int
    ) -> Optional[Dict[str, float]]:
        """
        Get GHG emissions data for a company (CDP-specific utility)

        Args:
            company_name: Company name
            year: Reporting year

        Returns:
            Dict with 'scope1', 'scope2', 'scope3' emissions (tCO2e) or None
        """
        reports = self.search_company(company_name=company_name, year=year)

        if not reports:
            return None

        # Extract emissions from source_metadata
        report = reports[0]
        metadata = report.source_metadata

        # Return emissions data if available
        scope1 = metadata.get('ghg_scope1')
        scope2 = metadata.get('ghg_scope2')
        scope3 = metadata.get('ghg_scope3')

        if scope1 is None and scope2 is None and scope3 is None:
            return None

        # Ensure type safety: convert to float or use 0.0 as default
        return {
            'scope1': float(scope1) if scope1 is not None else 0.0,
            'scope2': float(scope2) if scope2 is not None else 0.0,
            'scope3': float(scope3) if scope3 is not None else 0.0,
        }
