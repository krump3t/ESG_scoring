"""
Legacy SEC EDGAR Provider Implementation

**Deprecation Notice**: This module contains legacy methods preserved for
backward compatibility. New code should use SECEdgarProvider.fetch_10k().
"""

from typing import List, Dict, Optional
from .base_provider import CompanyReport
from .sec_edgar_provider import SECEdgarProvider

# ============================================================================
# LEGACY METHODS (Not part of Phase 1 enhanced implementation)
# These methods are preserved for backward compatibility but not actively maintained.
# Consider migrating to enhanced fetch_10k() API for new code.
# ============================================================================

class SECEdgarProviderLegacy(SECEdgarProvider):
    """Legacy methods from original SEC EDGAR provider.

    **Deprecation Notice**: These methods are not part of the Phase 1 enhanced
    implementation. Use SECEdgarProvider.fetch_10k() for new code.

    Preserved for backward compatibility only.
    """

    def _normalize_company_name(self, name: str) -> str:
        """
        Normalize company name for fuzzy matching

        Removes spaces, punctuation, and special characters
        Converts to lowercase

        Args:
            name: Company name

        Returns:
            Normalized name
        """
        import re
        # Remove common suffixes
        name = re.sub(r'\b(inc|corp|corporation|ltd|limited|llc|co|company)\b\.?', '', name, flags=re.IGNORECASE)
        # Remove punctuation and spaces
        name = re.sub(r'[^\w]', '', name)
        # Lowercase
        return name.lower()

    def _get_company_cik(self, company_name: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a company

        Uses fuzzy matching to handle variations like:
        - "ExxonMobil" → "Exxon Mobil Corporation"
        - "JPMorgan Chase" → "JPMorgan Chase & Co"

        Args:
            company_name: Company name

        Returns:
            CIK string (10 digits, zero-padded) or None
        """
        self._enforce_rate_limit()

        try:
            # Use SEC company tickers JSON (hosted on www.sec.gov, not data.sec.gov)
            url = f"{self.base_url}/files/company_tickers.json"

            response = requests.get(
                url,
                headers={'User-Agent': self.user_agent},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Normalize search term
            search_normalized = self._normalize_company_name(company_name)

            # Try exact substring match first (faster, handles most cases)
            company_lower = company_name.lower()
            for entry in data.values():
                if company_lower in entry['title'].lower():
                    cik = str(entry['cik_str']).zfill(10)
                    logger.info(f"Found CIK for {company_name}: {cik} (exact match)")
                    return cik

            # Fallback: fuzzy match with normalized names
            for entry in data.values():
                title_normalized = self._normalize_company_name(entry['title'])
                if search_normalized in title_normalized or title_normalized in search_normalized:
                    cik = str(entry['cik_str']).zfill(10)
                    logger.info(f"Found CIK for {company_name}: {cik} (fuzzy match: {entry['title']})")
                    return cik

            logger.warning(f"No CIK found for company: {company_name}")
            return None

        except Exception as e:
            logger.error(f"Failed to get CIK: {e}")
            return None

    def search_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,  # CIK or ticker
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search for company 10-K and 20-F annual reports

        Searches for:
        - 10-K: US domestic companies
        - 20-F: Foreign private issuers (e.g., Unilever, HSBC)

        Args:
            company_name: Company name
            company_id: CIK or ticker symbol
            year: Target year (fiscal year end)

        Returns:
            List of annual report filings (10-K and/or 20-F)
        """
        # Get CIK
        if company_id:
            cik = company_id.zfill(10) if company_id.isdigit() else self._get_company_cik(company_id)
        elif company_name:
            cik = self._get_company_cik(company_name)
        else:
            logger.error("Must provide company_name or company_id")
            return []

        if not cik:
            return []

        self._enforce_rate_limit()

        reports = []

        try:
            # Get company submissions
            url = f"{self.api_base}/submissions/CIK{cik}.json"

            response = requests.get(
                url,
                headers={'User-Agent': self.user_agent},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Extract 10-K filings
            filings = data.get('filings', {}).get('recent', {})
            forms = filings.get('form', [])
            filing_dates = filings.get('filingDate', [])
            accession_numbers = filings.get('accessionNumber', [])
            primary_documents = filings.get('primaryDocument', [])

            for i, form in enumerate(forms):
                # Check for both 10-K (domestic) and 20-F (foreign issuer) annual reports
                if form in ('10-K', '20-F'):
                    filing_date = filing_dates[i]
                    filing_year = int(filing_date[:4])

                    # Filter by year if specified
                    if year and filing_year != year:
                        continue

                    accession = accession_numbers[i].replace('-', '')
                    primary_doc = primary_documents[i]

                    # Construct document URL
                    doc_url = f"{self.base_url}/Archives/edgar/data/{cik}/{accession}/{primary_doc}"

                    report = CompanyReport(
                        company_name=data.get('name', company_name or ''),
                        company_id=cik,
                        year=filing_year,
                        report_type=form,  # '10-K' or '20-F'
                        report_title=f"{data.get('name')} {filing_year} Annual Report ({form})",
                        download_url=doc_url,
                        file_format='html',
                        file_size_bytes=None,
                        source='sec_edgar',
                        source_metadata={
                            'cik': cik,
                            'accession_number': accession_numbers[i],
                            'filing_date': filing_date,
                            'form': form,
                            'primary_document': primary_doc
                        },
                        date_published=filing_date,
                        date_retrieved=datetime.utcnow().strftime("%Y-%m-%d")
                    )

                    reports.append(report)

            logger.info(f"SEC EDGAR search: found {len(reports)} annual report(s) for {company_name or cik}")

        except Exception as e:
            logger.error(f"SEC EDGAR search failed: {e}")

        return reports

    def download_report(
        self,
        report: CompanyReport,
        output_path: str
    ) -> bool:
        """
        Download 10-K filing

        Args:
            report: CompanyReport from search_company()
            output_path: Local path to save HTML file

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
                headers={'User-Agent': self.user_agent},
                timeout=60
            )
            response.raise_for_status()

            # Save HTML
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)

            logger.info(f"Downloaded 10-K: {report.company_name} {report.year}")
            return True

        except Exception as e:
            logger.error(f"Failed to download 10-K: {e}")
            return False

    def list_available_companies(
        self,
        limit: int = 100
    ) -> List[Dict[str, str]]:
        """
        List companies with SEC filings

        Args:
            limit: Maximum companies to return

        Returns:
            List of company names and CIKs
        """
        self._enforce_rate_limit()

        companies = []

        try:
            # Get company tickers
            url = f"{self.api_base}/files/company_tickers.json"

            response = requests.get(
                url,
                headers={'User-Agent': self.user_agent},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Convert to list
            for i, entry in enumerate(data.values()):
                if i >= limit:
                    break

                companies.append({
                    'company_name': entry['title'],
                    'company_id': str(entry['cik_str']).zfill(10),
                    'ticker': entry['ticker']
                })

            logger.info(f"Listed {len(companies)} SEC companies")

        except Exception as e:
            logger.error(f"Failed to list SEC companies: {e}")

        return companies

    def extract_risk_factors(self, html_content: str) -> str:
        """
        Extract Item 1A (Risk Factors) from 10-K HTML

        Args:
            html_content: 10-K HTML content

        Returns:
            Extracted Risk Factors text
        """
        # Simple regex-based extraction
        # Item 1A typically appears as "ITEM 1A. RISK FACTORS" or similar

        patterns = [
            r'(?i)ITEM\s+1A[\.\s]+RISK\s+FACTORS(.*?)(?:ITEM\s+1B|ITEM\s+2)',
            r'(?i)<b>ITEM\s+1A[\.\s]+RISK\s+FACTORS</b>(.*?)<b>ITEM',
        ]

        for pattern in patterns:
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                risk_text = match.group(1)
                # Strip HTML tags
                risk_text = re.sub(r'<[^>]+>', '', risk_text)
                return risk_text.strip()

        logger.warning("Could not extract Item 1A Risk Factors from 10-K")
        return ""
