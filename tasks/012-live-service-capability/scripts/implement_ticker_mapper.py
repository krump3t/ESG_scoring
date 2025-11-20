"""
Task 012: Ticker Mapper Implementation (TDD)
Downloads authoritative SEC mapping and resolves Ticker -> CIK.
"""
import json
import logging
import requests
import sys
from pathlib import Path
from typing import Dict, Optional

# --- The Component (to be promoted to agents.crawler.ticker_mapper) ---
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

# --- The Verification Test ---
def test_ticker_resolution():
    # Configure logging to stdout
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    print("Initializing TickerMapper...")
    mapper = TickerMapper()

    test_cases = {
        "AAPL": "0000320193",
        "msft": "0000789019", # Case insensitive check
        "INVALID_TICKER_XYZ": None
    }

    print("\n--- Verifying Ticker Resolution ---")
    failures = 0
    for ticker, expected in test_cases.items():
        result = mapper.get_cik(ticker)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL": failures += 1
        print(f"Ticker: {ticker:<20} | Expected: {str(expected):<12} | Got: {str(result):<12} | {status}")

    if failures == 0:
        print("\nSUCCESS: TickerMapper is functional.")

        # PROMOTION: Write the verified component to the agents directory
        dest_path = Path("agents/crawler/ticker_mapper.py")
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract the class definition (simplified extraction for this script)
        # We read this file and slice out the Component section
        content = Path(__file__).read_text(encoding='utf-8')
        start_marker = "# --- The Component"
        end_marker = "# --- The Verification"

        code_block = content.split(start_marker)[1].split(end_marker)[0].strip()

        # Add necessary imports to the promoted file
        header = '"""Ticker Mapper: Resolves Stock Tickers to SEC CIKs."""\nimport json\nimport logging\nimport requests\nfrom pathlib import Path\nfrom typing import Dict, Optional\n\n'

        dest_path.write_text(header + code_block, encoding='utf-8')
        print(f"Promoted component to {dest_path}")

    else:
        print(f"\nFAILURE: {failures} tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    test_ticker_resolution()
