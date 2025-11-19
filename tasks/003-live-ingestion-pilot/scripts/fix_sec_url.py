"""
Fix SEC EDGAR company_tickers.json endpoint URL.

Issue: Provider uses data.sec.gov domain, but official docs specify www.sec.gov
Fix: Update COMPANY_TICKERS_URL to use correct domain

Author: SCA Protocol v13.8-MEA
Date: 2025-11-19
"""

import sys
from pathlib import Path

# Navigate to project root
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))

# Target file
SEC_EDGAR_PROVIDER_PATH = project_root / "agents" / "crawler" / "data_providers" / "sec_edgar_provider.py"

def main():
    print("Fixing SEC EDGAR company_tickers.json URL...")
    print(f"Target file: {SEC_EDGAR_PROVIDER_PATH}")
    print()

    # Read current file
    content = SEC_EDGAR_PROVIDER_PATH.read_text(encoding='utf-8')

    # Find and replace the incorrect URL pattern
    old_pattern = 'COMPANY_TICKERS_URL = f"{BASE_URL}/files/company_tickers.json"'
    new_pattern = 'COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"'

    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("[1/1] Patched COMPANY_TICKERS_URL")
        print(f"   OLD: COMPANY_TICKERS_URL = f\"{{BASE_URL}}/files/company_tickers.json\"")
        print(f"       (expands to: https://data.sec.gov/files/company_tickers.json)")
        print(f"   NEW: COMPANY_TICKERS_URL = \"https://www.sec.gov/files/company_tickers.json\"")
    else:
        print("[1/1] SKIP - Pattern not found")
        print()
        print("   Checking if already patched...")

        if 'COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"' in content:
            print("   Already patched correctly!")
            return 0
        else:
            print("   ERROR: Unexpected file content")
            return 1

    # Write modified content
    SEC_EDGAR_PROVIDER_PATH.write_text(content, encoding='utf-8')

    print()
    print("SUCCESS: SEC Tickers URL patched to use www.sec.gov")
    print()
    print("Rationale:")
    print("  - Official SEC API docs specify www.sec.gov domain")
    print("  - data.sec.gov/files/company_tickers.json returns 404")
    print("  - www.sec.gov/files/company_tickers.json is correct endpoint")
    print()
    print("Next step: Retry pilot script")

    return 0


if __name__ == "__main__":
    sys.exit(main())
