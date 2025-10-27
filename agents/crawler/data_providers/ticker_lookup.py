"""
Ticker Symbol Lookup Provider

Resolves company names to ticker symbols and SEC CIK numbers using fuzzy matching
on the official SEC company_tickers.json dataset (10,000+ public companies).

Data Sources:
- SEC company_tickers.json (local cached copy, updated quarterly)
  - 10,142 public companies as of 2025-Q4
  - Direct company name → ticker → CIK mapping
  - Fuzzy matching for name variations

This provider uses LOCAL data only (no external API calls) to ensure:
- Deterministic results
- No dependency on external API availability/authentication
- Full compliance with SCA Authentic Computation invariant
"""

import json
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import time
from difflib import SequenceMatcher

from agents.crawler.data_providers.base_provider import BaseDataProvider, CompanyReport
from libs.utils.clock import get_clock
clock = get_clock()


class TickerLookupProvider(BaseDataProvider):
    """
    Ticker symbol lookup provider for company name disambiguation

    Tier 2 utility provider that resolves company name edge cases by:
    1. Fuzzy match Company Name against SEC dataset (10,142 companies)
    2. Extract Ticker Symbol + CIK from best match
    3. Return CIK for retry with SEC EDGAR provider

    Use cases:
    - Company name variations (e.g., "JPMorgan Chase" vs "JP Morgan" vs "JPMorgan Chase & Co")
    - Parent/subsidiary entity disambiguation
    - Resolving common name abbreviations

    Features:
    - Uses local cached SEC company_tickers.json (no external API dependencies)
    - Fuzzy matching with SequenceMatcher (similarity threshold ≥0.8)
    - Deterministic results (same input always returns same output)
    - Full compliance with SCA Authentic Computation invariant
    """

    def __init__(self, data_dir: Optional[Path] = None, rate_limit: float = 0.1):
        """
        Initialize ticker lookup provider

        Args:
            data_dir: Directory containing company_tickers.json (auto-detected if None)
            rate_limit: Minimum seconds between requests (default 0.1 = 10 req/sec)
        """
        super().__init__(source_id="ticker_lookup", rate_limit=rate_limit)

        # Auto-detect data directory (task/data/ or project/data/)
        if data_dir is None:
            # Try task-specific data directory first
            data_dir = Path(__file__).parents[3] / "tasks" / "007-tier2-data-providers" / "data"
            if not data_dir.exists():
                # Fallback to project data directory
                data_dir = Path(__file__).parents[2] / "data"

        self.data_dir = Path(data_dir)
        self.sec_tickers_file = self.data_dir / "company_tickers.json"

        # Load SEC dataset on initialization
        self.company_data: Dict[str, Any] = {}
        self._load_sec_dataset()

    def search_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[CompanyReport]:
        """
        Search for company ticker and CIK

        Pipeline:
        1. Lookup ticker symbol (Yahoo Finance → AlphaVantage fallback)
        2. Map ticker → CIK using SEC official dataset
        3. Return CIK as metadata for SEC EDGAR retry

        Args:
            company_name: Company name
            company_id: Ticker symbol (if already known)
            year: Year (metadata only, not used in lookup)

        Returns:
            List with single CompanyReport containing ticker → CIK mapping
        """
        if not company_name and not company_id:
            return []

        self._enforce_rate_limit()

        try:
            # Step 1: Get ticker symbol
            if company_id:
                ticker = company_id
                lookup_method = "direct"
                used_fallback = False
            else:
                ticker, lookup_method, used_fallback = self._lookup_ticker(company_name)

            if not ticker:
                return []

            # Step 2: Map ticker → CIK
            cik = self._ticker_to_cik(ticker)

            if not cik:
                return []

            # Step 3: Return mapping as metadata
            metadata = {
                "ticker": ticker,
                "cik": cik,
                "lookup_method": lookup_method,
            }
            if used_fallback:
                metadata["alphavantage_fallback"] = True

            report = CompanyReport(
                company_name=company_name or ticker,
                company_id=cik,
                year=year if year else clock.now().year,
                report_type="ticker_cik_mapping",
                report_title=f"Ticker-CIK Mapping: {ticker} → {cik}",
                download_url=None,  # No downloadable report
                file_format="json",
                file_size_bytes=None,
                source="ticker_lookup",
                source_metadata=metadata,
                date_published=None,
                date_retrieved=clock.now().strftime("%Y-%m-%d"),
            )

            return [report]

        except requests.exceptions.Timeout:
            return []
        except requests.exceptions.ConnectionError:
            return []
        except Exception:
            return []

    def _load_sec_dataset(self) -> None:
        """
        Load SEC company_tickers.json dataset into memory

        Raises:
            FileNotFoundError: If company_tickers.json not found in data directory
        """
        if not self.sec_tickers_file.exists():
            raise FileNotFoundError(
                f"SEC dataset not found: {self.sec_tickers_file}\n"
                f"Please download from https://www.sec.gov/files/company_tickers.json"
            )

        with open(self.sec_tickers_file, 'r') as f:
            self.company_data = json.load(f)

    def _normalize_company_name(self, name: str) -> str:
        """
        Normalize company name for fuzzy matching

        Removes common suffixes, punctuation, and standardizes whitespace.

        Args:
            name: Company name

        Returns:
            Normalized company name
        """
        # Convert to uppercase for case-insensitive matching
        normalized = name.upper()

        # Remove common corporate suffixes (LONGEST FIRST to avoid partial matches)
        suffixes = [
            "INCORPORATED", "CORPORATION", "LIMITED", "COMPANY", "HOLDINGS",
            "INC", "CORP", "LTD", "LLC", "LLP", "PLC", "CO", "GROUP",
            "& CO", "&CO"
        ]

        for suffix in suffixes:
            # Remove suffix with or without punctuation
            normalized = normalized.replace(f" {suffix}.", "")
            normalized = normalized.replace(f" {suffix}", "")

        # Remove punctuation
        for char in [".", ",", "'", "-", "&"]:
            normalized = normalized.replace(char, " ")

        # Normalize whitespace
        normalized = " ".join(normalized.split())

        return normalized.strip()

    def _fuzzy_match_company(
        self,
        company_name: str,
        threshold: float = 0.8
    ) -> Optional[tuple[str, str, str, float]]:
        """
        Fuzzy match company name against SEC dataset

        Uses SequenceMatcher for similarity scoring on normalized company names.

        Args:
            company_name: Company name to match
            threshold: Minimum similarity score (0.0-1.0, default 0.8)

        Returns:
            Tuple of (ticker, cik, matched_title, similarity_score) or None
        """
        if not company_name:
            return None

        normalized_query = self._normalize_company_name(company_name)

        best_match = None
        best_score = 0.0

        for entry in self.company_data.values():
            title = entry.get("title", "")
            normalized_title = self._normalize_company_name(title)

            # Calculate similarity using SequenceMatcher
            similarity = SequenceMatcher(None, normalized_query, normalized_title).ratio()

            # Check for exact match on normalized names (score = 1.0)
            if normalized_query == normalized_title:
                ticker = entry.get("ticker", "")
                cik = str(entry.get("cik_str", "")).zfill(10)
                return (ticker, cik, title, 1.0)

            # Track best partial match
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = (
                    entry.get("ticker", ""),
                    str(entry.get("cik_str", "")).zfill(10),
                    title,
                    similarity
                )

        return best_match

    def _lookup_ticker(self, company_name: Optional[str]) -> tuple[Optional[str], str, bool]:
        """
        Lookup ticker symbol for company name using fuzzy matching on SEC dataset

        Args:
            company_name: Company name

        Returns:
            Tuple of (ticker_symbol, lookup_method, used_fallback)
            Note: used_fallback is always False (no external API fallback)
        """
        if not company_name:
            return (None, "none", False)

        # Fuzzy match against SEC dataset
        match_result = self._fuzzy_match_company(company_name, threshold=0.8)

        if match_result:
            ticker, cik, matched_title, similarity = match_result
            # Lookup method indicates fuzzy matching (not external API)
            return (ticker, "sec_fuzzy_match", False)

        return (None, "none", False)

    def _ticker_to_cik(self, ticker: str) -> Optional[str]:
        """
        Map ticker symbol to SEC CIK using local SEC dataset

        Args:
            ticker: Ticker symbol (e.g., "AAPL")

        Returns:
            Zero-padded 10-digit CIK (e.g., "0000320193") or None
        """
        if not ticker:
            return None

        # Search for matching ticker (case-insensitive) in local dataset
        ticker_upper = ticker.upper()
        for entry in self.company_data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                cik_str = str(entry.get("cik_str", ""))
                # Zero-pad to 10 digits
                return cik_str.zfill(10)

        return None

    def download_report(
        self,
        report: CompanyReport,
        output_path: str
    ) -> bool:
        """
        Download not supported for ticker lookup

        Ticker lookup provides metadata only (ticker → CIK mapping),
        not downloadable reports.

        Returns:
            False (always)
        """
        return False

    def list_available_companies(
        self,
        limit: int = 100
    ) -> List[Dict[str, str]]:
        """
        List available companies from local SEC company tickers dataset

        Args:
            limit: Maximum number of companies to return

        Returns:
            List of dicts with 'company_name', 'company_id' (CIK), and 'ticker'
        """
        self._enforce_rate_limit()

        companies = []
        for entry in list(self.company_data.values())[:limit]:
            companies.append({
                "company_name": entry.get("title", ""),
                "company_id": str(entry.get("cik_str", "")).zfill(10),
                "ticker": entry.get("ticker", ""),
            })

        return companies
