"""Guarded SEC EDGAR provider with polite caching behaviour."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests  # @allow-network: integration tests may call the SEC API

from libs.utils import env

logger = logging.getLogger(__name__)

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
SEC_INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json"

REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 0.5
REQUEST_COOLDOWN_SECONDS = 0.2

DATA_ROOT = Path(env.get("DATA_ROOT", "artifacts"))
SEC_CACHE_ROOT = DATA_ROOT / "ingestion" / "sec"
SEC_CACHE_ROOT.mkdir(parents=True, exist_ok=True)

_last_request_ts: float = 0.0
_ticker_cache: Optional[list[Dict[str, object]]] = None


class SECIntegrationError(RuntimeError):
    """Raised when SEC integration fails in live mode."""


def fetch_10k(company: str, year: int, *, allow_network: Optional[bool] = None) -> Path:
    """Download and cache a 10-K filing PDF for ``company`` and ``year``."""

    network_allowed = env.bool_flag("ALLOW_NETWORK") if allow_network is None else allow_network
    if not network_allowed:
        raise PermissionError("ALLOW_NETWORK=false. Enable to fetch SEC filings.")

    user_agent = env.get("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise RuntimeError("SEC_USER_AGENT is required to access the SEC API.")

    identifiers = _resolve_company(company.strip(), user_agent=user_agent)
    company_slug = _sanitize_company(company)
    company_dir = SEC_CACHE_ROOT / company_slug / str(year)
    company_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = company_dir / "10-K.pdf"
    ledger_path = company_dir / "ledger.json"

    if _is_cached(pdf_path, ledger_path):
        return pdf_path

    if pdf_path.exists():
        pdf_path.unlink()
    if ledger_path.exists():
        ledger_path.unlink()

    filing = _find_filing(identifiers["cik"], year, user_agent=user_agent)
    accession_compact = filing["accessionNumber"].replace("-", "")
    document_name = _select_document(
        identifiers["cik"],
        accession_compact,
        filing["primaryDocument"],
        user_agent=user_agent,
    )
    document_url = SEC_ARCHIVES_URL.format(
        cik=int(identifiers["cik"]),
        accession=accession_compact,
        document=document_name,
    )

    logger.info(
        "Downloading SEC 10-K company=%s year=%s accession=%s document=%s",
        company,
        year,
        filing["accessionNumber"],
        document_name,
    )

    pdf_bytes, status_code = _http_get(document_url, user_agent=user_agent)
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    temp_pdf = pdf_path.with_suffix(".tmp")
    temp_pdf.write_bytes(pdf_bytes)
    temp_pdf.replace(pdf_path)

    ledger = {
        "company": company,
        "company_slug": company_slug,
        "ticker": identifiers.get("ticker"),
        "cik": identifiers["cik"],
        "year": year,
        "document": document_name,
        "accession_number": filing["accessionNumber"],
        "request": {
            "url": document_url,
            "status": status_code,
            "user_agent": user_agent,
            "fetched_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        },
        "sha256": sha256,
    }
    temp_ledger = ledger_path.with_suffix(".tmp")
    temp_ledger.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    temp_ledger.replace(ledger_path)

    return pdf_path


def _resolve_company(company: str, *, user_agent: str) -> Dict[str, str]:
    """Return {'cik': str, 'ticker': str | None} for the provided company."""

    stripped = company.strip()
    if stripped.isdigit():
        return {"cik": stripped.zfill(10), "ticker": ""}

    mapping = _load_ticker_map(user_agent=user_agent)
    company_key = _normalize_key(company)

    # First try direct ticker match
    for entry in mapping:
        ticker = str(entry.get("ticker", "")).upper()
        if ticker and _normalize_key(ticker) == company_key:
            cik_str = str(entry.get("cik_str", "")).zfill(10)
            return {"cik": cik_str, "ticker": ticker}

    # Fallback: match by company title
    for entry in mapping:
        title = str(entry.get("title", ""))
        if title and _normalize_key(title) == company_key:
            cik_str = str(entry.get("cik_str", "")).zfill(10)
            ticker = str(entry.get("ticker", "")).upper()
            return {"cik": cik_str, "ticker": ticker}

    raise SECIntegrationError(f"Unable to resolve company '{company}' to a CIK.")


def _load_ticker_map(*, user_agent: str) -> list[Dict[str, object]]:
    global _ticker_cache
    if _ticker_cache is not None:
        return _ticker_cache

    cache_path = SEC_CACHE_ROOT / "company_tickers.json"
    if cache_path.exists():
        mapping_bytes = cache_path.read_bytes()
    else:
        logger.info("Fetching SEC ticker map…")
        mapping_bytes, _ = _http_get(SEC_TICKER_URL, user_agent=user_agent)
        cache_path.write_bytes(mapping_bytes)

    data = json.loads(mapping_bytes.decode("utf-8"))
    # The SEC file is an array of objects; convert dict-of-dicts if needed.
    if isinstance(data, dict):
        values = list(data.values())
    else:
        values = list(data)

    _ticker_cache = values
    return values


def _find_filing(cik: str, year: int, *, user_agent: str) -> Dict[str, str]:
    submissions_bytes, _ = _http_get(SEC_SUBMISSIONS_URL.format(cik=cik), user_agent=user_agent)
    submissions = json.loads(submissions_bytes.decode("utf-8"))
    filings = submissions.get("filings", {}).get("recent", {})

    for idx, form in enumerate(filings.get("form", [])):
        if form != "10-K":
            continue
        filing_year = filings.get("fy", [""])[idx]
        if str(filing_year).isdigit() and int(filing_year) == int(year):
            return {
                "accessionNumber": filings["accessionNumber"][idx],
                "primaryDocument": filings["primaryDocument"][idx],
            }

    raise SECIntegrationError(f"No 10-K found for CIK {cik} in {year}.")


def _select_document(cik: str, accession: str, primary_document: str, *, user_agent: str) -> str:
    """Prefer a PDF document if present in the filing directory."""

    index_url = SEC_INDEX_URL.format(cik=int(cik), accession=accession)
    try:
        index_bytes, _ = _http_get(index_url, user_agent=user_agent)
        index_data = json.loads(index_bytes.decode("utf-8"))
    except SECIntegrationError:
        logger.debug("Filing index unavailable, using primary document %s", primary_document)
        return primary_document

    directory_items = index_data.get("directory", {}).get("item", [])
    for item in directory_items:
        name = str(item.get("name", ""))
        if name.lower().endswith(".pdf") and "10-k" in name.lower():
            return name

    logger.debug("No PDF found in index, using primary document %s", primary_document)
    return primary_document


def _http_get(url: str, *, user_agent: str) -> Tuple[bytes, int]:
    headers = {"User-Agent": user_agent}
    for attempt in range(MAX_RETRIES):
        _respect_min_delay()
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            logger.warning("SEC request error (%s/%s): %s", attempt + 1, MAX_RETRIES, exc)
            _backoff(attempt)
            continue

        if response.status_code in {403, 429}:
            logger.warning(
                "SEC returned status %s for %s (attempt %s/%s)",
                response.status_code,
                url,
                attempt + 1,
                MAX_RETRIES,
            )
            _backoff(attempt)
            continue

        if response.status_code >= 400:
            raise SECIntegrationError(f"SEC request failed: {url} status={response.status_code}")

        return response.content, response.status_code

    raise SECIntegrationError(f"Failed to download {url} after {MAX_RETRIES} attempts.")


def _is_cached(pdf_path: Path, ledger_path: Path) -> bool:
    if not pdf_path.exists() or not ledger_path.exists():
        return False

    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Corrupt SEC ledger at %s; re-fetching.", ledger_path)
        return False

    recorded_sha = ledger.get("sha256")
    if not recorded_sha:
        logger.warning("Ledger missing sha256 at %s; re-fetching.", ledger_path)
        return False

    current_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if current_sha != recorded_sha:
        logger.warning("SEC cache hash mismatch for %s; refreshing.", pdf_path)
        return False

    return True


def _respect_min_delay() -> None:
    global _last_request_ts
    now = time.monotonic()
    elapsed = now - _last_request_ts
    if elapsed < REQUEST_COOLDOWN_SECONDS:
        time.sleep(REQUEST_COOLDOWN_SECONDS - elapsed)
    _last_request_ts = time.monotonic()


def _backoff(attempt: int) -> None:
    delay = BACKOFF_BASE_SECONDS * (2**attempt)
    time.sleep(delay)


def _sanitize_company(company: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]+", "-", company.lower())
    return sanitized.strip("-") or "company"


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())
