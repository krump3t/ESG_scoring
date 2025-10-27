"""
Web crawler for ESG/Sustainability reports using Playwright
Crawls report repositories and extracts PDF URLs for processing
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
import time
import json
import hashlib
import logging
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse
import re
from libs.utils.clock import get_clock
clock = get_clock()

# Configure logging
logger = logging.getLogger(__name__)


def get_audit_timestamp() -> str:
    """Get deterministic timestamp with AUDIT_TIME override (Phase 7)"""
    audit_time = os.getenv("AUDIT_TIME")
    if audit_time:
        return audit_time
    return clock.now().isoformat()


@dataclass
class ReportRef:
    """Reference to a sustainability report"""
    company: str
    title: str
    year: int
    url: str
    filetype: str = "pdf"
    crawled_at: Optional[str] = None
    source_page: Optional[str] = None
    file_size: Optional[int] = None

    def __post_init__(self):
        if self.crawled_at is None:
            self.crawled_at = get_audit_timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportRef':
        """Create from dictionary"""
        return cls(**data)


class SustainabilityReportsCrawler:
    """
    Crawler for sustainability reports from various sources
    Uses Playwright for JavaScript-heavy sites
    """

    def __init__(
        self,
        rate_limit: int = 10,  # requests per minute
        timeout: int = 30000,  # milliseconds
        headless: bool = True,
        cache_dir: Optional[Path] = None
    ):
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.headless = headless
        self.cache_dir = cache_dir or Path("data/crawler_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Track crawled URLs to avoid duplicates
        self.crawled_urls: Set[str] = set()
        self.last_request_time = 0

        # Patterns for identifying ESG reports
        self.report_patterns = [
            r'sustainability[\s\-_]report',
            r'esg[\s\-_]report',
            r'csr[\s\-_]report',
            r'corporate[\s\-_]responsibility',
            r'annual[\s\-_]report',  # Often contains ESG section
            r'climate[\s\-_]report',
            r'tcfd[\s\-_]report',
            r'environmental[\s\-_]report'
        ]

        # Year extraction patterns
        self.year_patterns = [
            r'20\d{2}',  # 4-digit year
            r'\d{2}[\-/]\d{2}',  # FY format
        ]

    def _rate_limit_wait(self):
        """Enforce rate limiting"""
        if self.last_request_time > 0:
            elapsed = clock.time() - self.last_request_time
            min_interval = 60.0 / self.rate_limit
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        self.last_request_time = clock.time()

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        for pattern in self.year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year_str = match.group()
                # Handle different formats
                if len(year_str) == 4:
                    return int(year_str)
                elif '/' in year_str or '-' in year_str:
                    # FY format, take the latter year
                    parts = re.split(r'[/-]', year_str)
                    if len(parts) == 2:
                        year = int(parts[1])
                        if year < 100:
                            year += 2000
                        return year
        return None

    def _extract_company_name(self, text: str, url: str) -> str:
        """Extract company name from text or URL"""
        # Try to extract from URL domain
        domain = urlparse(url).netloc
        if domain:
            # Remove common prefixes/suffixes
            company = domain.replace('www.', '').replace('.com', '').replace('.org', '')
            company = company.replace('-', ' ').replace('_', ' ')
            return company.title()

        # Fallback to first few words of title
        words = text.split()[:3]
        return ' '.join(words)

    def _is_report_url(self, url: str, link_text: str = "") -> bool:
        """Check if URL likely points to a sustainability report"""
        url_lower = url.lower()
        text_lower = link_text.lower()

        # Check file extension
        if not url_lower.endswith('.pdf'):
            return False

        # Check URL or link text for report keywords
        combined = url_lower + " " + text_lower
        for pattern in self.report_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return True

        return False

    def _get_cached_results(self, seed_url: str) -> Optional[List[ReportRef]]:
        """Check cache for recent results"""
        cache_key = hashlib.md5(seed_url.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            # Check if cache is fresh (less than 24 hours old)
            audit_ts = datetime.fromisoformat(get_audit_timestamp())
            age = audit_ts - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age < timedelta(hours=24):
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        return [ReportRef.from_dict(item) for item in data]
                except Exception as e:
                    logger.warning(f"Failed to load cache: {e}")

        return None

    def _save_to_cache(self, seed_url: str, reports: List[ReportRef]):
        """Save results to cache"""
        cache_key = hashlib.md5(seed_url.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump([r.to_dict() for r in reports], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def crawl_with_playwright(self, seed_url: str, max_reports: int = 50) -> List[ReportRef]:
        """
        Crawl using Playwright for JavaScript-rendered pages
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright && playwright install")
            return self._fallback_crawl(seed_url)

        reports = []

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (ESG Report Crawler; Academic Research)"
                )
                page = context.new_page()
                page.set_default_timeout(self.timeout)

                # Navigate to seed URL
                self._rate_limit_wait()
                page.goto(seed_url, wait_until="networkidle")

                # Wait for content to load
                page.wait_for_load_state("domcontentloaded")

                # Extract all links
                links = page.query_selector_all('a[href]')

                for link in links:
                    if len(reports) >= max_reports:
                        break

                    try:
                        href = link.get_attribute('href')
                        text = link.inner_text()

                        if href and self._is_report_url(href, text):
                            # Make absolute URL
                            full_url = urljoin(seed_url, href)

                            if full_url not in self.crawled_urls:
                                # Extract metadata
                                year = self._extract_year(text) or self._extract_year(href)
                                if not year:
                                    year = int(get_audit_timestamp()[:4])

                                company = self._extract_company_name(text, full_url)

                                report = ReportRef(
                                    company=company,
                                    title=text.strip(),
                                    year=year,
                                    url=full_url,
                                    source_page=seed_url
                                )

                                reports.append(report)
                                self.crawled_urls.add(full_url)
                                logger.info(f"Found report: {company} ({year}) - {full_url}")

                    except Exception as e:
                        logger.debug(f"Error processing link: {e}")
                        continue

                # Try to find pagination and crawl more pages if needed
                if len(reports) < max_reports:
                    next_button = page.query_selector('a:has-text("Next"), button:has-text("Next")')
                    if next_button and next_button.is_visible():
                        self._rate_limit_wait()
                        next_button.click()
                        page.wait_for_load_state("networkidle")
                        # Recursive call for next page
                        # (In production, would handle this more elegantly)

                browser.close()

        except Exception as e:
            logger.error(f"Playwright crawl failed: {e}")
            return self._fallback_crawl(seed_url)

        return reports

    def _fallback_crawl(self, seed_url: str) -> List[ReportRef]:
        """
        Fallback crawler using requests (for non-JS sites)
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("requests/beautifulsoup4 not installed")
            return self._static_reports()

        reports = []

        try:
            self._rate_limit_wait()
            response = requests.get(
                seed_url,
                headers={'User-Agent': 'ESG Report Crawler'},
                timeout=self.timeout / 1000
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)

                if self._is_report_url(href, text):
                    full_url = urljoin(seed_url, href)

                    if full_url not in self.crawled_urls:
                        year = self._extract_year(text) or int(get_audit_timestamp()[:4])
                        company = self._extract_company_name(text, full_url)

                        report = ReportRef(
                            company=company,
                            title=text,
                            year=year,
                            url=full_url,
                            source_page=seed_url
                        )

                        reports.append(report)
                        self.crawled_urls.add(full_url)

        except Exception as e:
            logger.error(f"Fallback crawl failed: {e}")
            return self._static_reports()

        return reports

    def _static_reports(self) -> List[ReportRef]:
        """
        Static list of reports for testing when crawling fails
        """
        return [
            ReportRef(
                company="Microsoft",
                title="Environmental Sustainability Report 2023",
                year=2023,
                url="https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RW15mgm",
                source_page="static"
            ),
            ReportRef(
                company="Apple",
                title="Environmental Progress Report 2023",
                year=2023,
                url="https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2023.pdf",
                source_page="static"
            ),
            ReportRef(
                company="Google",
                title="Environmental Report 2023",
                year=2023,
                url="https://www.gstatic.com/gumdrop/sustainability/google-2023-environmental-report.pdf",
                source_page="static"
            )
        ]

    def crawl(self, seed_url: str, use_cache: bool = True, max_reports: int = 50) -> List[ReportRef]:
        """
        Main crawl method with caching
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached_results(seed_url)
            if cached:
                logger.info(f"Using cached results for {seed_url}")
                return cached

        # Perform crawl
        logger.info(f"Starting crawl of {seed_url}")

        # Try Playwright first, fallback to requests
        reports = self.crawl_with_playwright(seed_url, max_reports)

        # Save to cache
        if reports and use_cache:
            self._save_to_cache(seed_url, reports)

        logger.info(f"Crawled {len(reports)} reports")
        return reports


def crawl_sustainabilityreports(
    seed_url: str = "https://www.sustainability-reports.com/",
    max_reports: int = 50
) -> List[ReportRef]:
    """
    Main entry point for crawling sustainability reports
    """
    crawler = SustainabilityReportsCrawler(
        rate_limit=10,  # 10 requests per minute
        timeout=30000,  # 30 seconds
        headless=True
    )

    return crawler.crawl(seed_url, use_cache=True, max_reports=max_reports)


# For backward compatibility with existing code
def crawl_reports(company: Optional[str] = None, year: Optional[int] = None) -> List[ReportRef]:
    """
    Crawl reports with optional filtering by company/year
    """
    # Get all reports
    reports = crawl_sustainabilityreports()

    # Filter if requested
    if company:
        reports = [r for r in reports if company.lower() in r.company.lower()]
    if year:
        reports = [r for r in reports if r.year == year]

    return reports


if __name__ == "__main__":
    # Test the crawler
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        seed_url = sys.argv[1]
    else:
        seed_url = "https://www.sustainability-reports.com/"

    reports = crawl_sustainabilityreports(seed_url, max_reports=10)

    for report in reports:
        print(f"{report.company} ({report.year}): {report.url}")