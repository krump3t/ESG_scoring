"""
SEC EDGAR Provider - Real, Polite, Fail-Closed

Fetches 10-K/10-Q filings from SEC EDGAR with:
- Proper User-Agent identification (required by SEC)
- Rate limiting (configurable; default 1 req/sec; SEC guideline < 10 rps)
- HTTP manifest tracking (source_url, request/response headers, SHA256)
- Fail-closed on errors (no mocking)
"""

from __future__ import annotations
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterable
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None


SEC_BASE = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar"

# User-Agent: SEC requires identification; must match pattern
UA = os.environ.get(
    "SEC_USER_AGENT",
    "ESG-Scoring/1.0 (contact=missing@example.com; purpose=educational)"
)


def _rate_limit_sleep():
    """Enforce rate limiting between SEC requests."""
    delay = float(os.environ.get("SEC_RPS_DELAY", "1.0"))
    if delay > 0:
        time.sleep(delay)


@dataclass
class ManifestEntry:
    """HTTP transaction record for SEC document fetch."""
    source_url: str
    request_headers: Dict[str, str]
    response_headers: Dict[str, str]
    sha256_raw: str
    size_bytes: int
    fetched_at: str  # ISO 8601 UTC, real timestamp
    provider: str = "sec_edgar"

    def to_dict(self):
        return asdict(self)


class SecEdgarClient:
    """
    Client for SEC EDGAR document fetching.

    Real implementation:
    - Uses requests library for HTTP
    - Respects SEC rate limits
    - Tracks all HTTP manifests
    - Fail-closed: raises on any error (no mocking)
    """

    def __init__(self, session: Optional[requests.Session] = None):
        """
        Initialize SEC client.

        Args:
            session: Optional pre-configured requests.Session
        """
        if not requests:
            raise ImportError("requests library required for SecEdgarClient")

        self.s = session or requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Accept-Encoding": "gzip, deflate"
        })
        self.s.timeout = 30

    def _get_json(self, url: str) -> Dict[str, Any]:
        """
        Fetch JSON from SEC API with rate limiting.

        Args:
            url: SEC API endpoint

        Returns:
            Parsed JSON response

        Raises:
            RuntimeError: On HTTP error or parse failure
        """
        _rate_limit_sleep()

        try:
            r = self.s.get(url, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(
                    f"sec_api_error: {url} status={r.status_code} text={r.text[:100]}"
                )
            return r.json()
        except requests.RequestException as e:
            raise RuntimeError(f"sec_api_fetch_failed: {url} error={e}")

    def _get_stream(self, url: str) -> tuple[requests.Response, Dict[str, str]]:
        """
        Fetch document as stream with manifest.

        Args:
            url: Document URL (SEC Archives or external)

        Returns:
            (Response object, request headers dict)

        Raises:
            RuntimeError: On HTTP error
        """
        _rate_limit_sleep()

        try:
            r = self.s.get(url, stream=True, timeout=60)
            if r.status_code != 200:
                raise RuntimeError(
                    f"sec_doc_fetch_failed: {url} status={r.status_code}"
                )
            req_headers = {k: v for k, v in self.s.headers.items()}
            return r, req_headers
        except requests.RequestException as e:
            raise RuntimeError(f"sec_doc_fetch_error: {url} error={e}")

    def resolve_cik(self, ticker_or_cik: str) -> str:
        """
        Resolve ticker to CIK using SEC JSON tickers file.

        Args:
            ticker_or_cik: Ticker symbol or CIK string

        Returns:
            Numeric CIK string, zero-padded to 10 digits

        Raises:
            RuntimeError: If resolution fails
        """
        # If already numeric, assume it's a CIK
        if re.fullmatch(r"\d{1,10}", str(ticker_or_cik)):
            return str(ticker_or_cik).zfill(10)

        # Attempt ticker lookup
        try:
            url = f"{SEC_BASE}/files/company_tickers.json"
            tickers_data = self._get_json(url)

            # tickers_data is dict: { "0": {"cik_str": ..., "ticker": ...}, ... }
            for entry in tickers_data.values():
                if entry.get("ticker", "").upper() == str(ticker_or_cik).upper():
                    cik = str(entry.get("cik_str", "")).zfill(10)
                    return cik

            raise RuntimeError(f"ticker_not_found_in_sec_tickers: {ticker_or_cik}")

        except Exception as e:
            raise RuntimeError(f"cik_resolution_failed: {ticker_or_cik} error={e}")

    def list_10k_filings(self, cik: str, year: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        List 10-K filings for a company in a given year.

        Args:
            cik: Company CIK (numeric, zero-padded)
            year: Target year (e.g., 2024)
            limit: Max number of filings to return

        Returns:
            List of filing dicts with keys: accession, filing_date, form, primary_doc_url

        Raises:
            RuntimeError: On API error or missing data
        """
        url = f"{SEC_BASE}/submissions/CIK{cik}.json"
        data = self._get_json(url)

        filings = []
        try:
            recent = data.get("filings", {}).get("recent", {})

            # Extract parallel arrays
            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            dates = recent.get("filingDate", [])
            urls = recent.get("primaryDocument", [])

            # Iterate and filter for 10-K in target year
            for form, accession, date, primary_doc in zip(forms, accessions, dates, urls):
                if form != "10-K":
                    continue

                # Check year from filing date (YYYY-MM-DD format)
                filing_year = int(date.split("-")[0])
                if filing_year != year:
                    continue

                # Build full URL to primary document
                doc_url = f"{SEC_ARCHIVES}/data/{cik}/{accession.replace('-','')}/{primary_doc}"

                filings.append({
                    "accession": accession,
                    "filing_date": date,
                    "form": "10-K",
                    "primary_doc_url": doc_url,
                    "primary_doc": primary_doc,
                })

                if len(filings) >= limit:
                    break

        except Exception as e:
            raise RuntimeError(f"10k_parsing_failed: cik={cik} error={e}")

        if not filings:
            raise RuntimeError(f"no_10k_found: cik={cik} year={year}")

        return filings

    def download_document(self, url: str, dest: Path) -> ManifestEntry:
        """
        Download document with manifest tracking.

        Args:
            url: Full URL to document (e.g., SEC Archives PDF)
            dest: Destination file path

        Returns:
            ManifestEntry with HTTP metadata

        Raises:
            RuntimeError: On download failure
        """
        dest.parent.mkdir(parents=True, exist_ok=True)

        r, req_headers = self._get_stream(url)

        sha = hashlib.sha256()
        size = 0

        try:
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    sha.update(chunk)
                    size += len(chunk)
        except Exception as e:
            raise RuntimeError(f"document_write_failed: {dest} error={e}")

        fetched_at = datetime.now(timezone.utc).isoformat()

        resp_headers = {k: v for k, v in r.headers.items()}

        return ManifestEntry(
            source_url=url,
            request_headers=req_headers,
            response_headers=resp_headers,
            sha256_raw=sha.hexdigest(),
            size_bytes=size,
            fetched_at=fetched_at,
        )


if __name__ == "__main__":
    # Test connectivity
    client = SecEdgarClient()
    print("SecEdgarClient initialized successfully")
