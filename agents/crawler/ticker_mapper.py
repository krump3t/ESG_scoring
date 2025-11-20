"""Ticker Mapper: Resolves Stock Tickers to SEC CIKs."""
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Optional


class TickerMapper:
    SEC_MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"

    def __init__(self, local_cache_path: str = "artifacts/company_tickers.json"):
        self.local_cache = Path(local_cache_path)
        self.mapping: Dict[str, str] = {} # Ticker -> CIK
        self._load_data()

    def _load_data(self):
        """Loads mapping from local cache or downloads from SEC."""
        if not self.local_cache.exists():
            self._refresh_cache()

        if self.local_cache.exists():
            try:
                data = json.loads(self.local_cache.read_text(encoding='utf-8'))
                # Parse SEC format: {"0": {"cik_str": 320193, "ticker": "AAPL", ...}, ...}
                for _, entry in data.items():
                    ticker = entry.get("ticker", "").upper()
                    cik_raw = entry.get("cik_str", "")
                    if ticker and cik_raw:
                        # CIK must be 10 digits, zero-padded
                        self.mapping[ticker] = str(cik_raw).zfill(10)
            except Exception as e:
                logging.error(f"Failed to parse ticker map: {e}")

    def _refresh_cache(self):
        """Downloads fresh mapping from SEC."""
        headers = {"User-Agent": "ESG-Analysis-Bot/1.0 (contact@example.com)"}
        try:
            logging.info(f"Downloading SEC tickers from {self.SEC_MAPPING_URL}...")
            resp = requests.get(self.SEC_MAPPING_URL, headers=headers, timeout=10)
            resp.raise_for_status()

            self.local_cache.parent.mkdir(parents=True, exist_ok=True)
            self.local_cache.write_text(json.dumps(resp.json(), indent=2))
            logging.info("Ticker cache updated.")
        except Exception as e:
            logging.warning(f"Could not download tickers: {e}")

    def get_cik(self, ticker: str) -> Optional[str]:
        """Returns 10-digit CIK for a given ticker."""
        return self.mapping.get(ticker.upper())