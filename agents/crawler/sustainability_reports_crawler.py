"""
Production-grade web crawler for ESG/Sustainability reports.

Primary target: SustainabilityReports.com (50,000+ corporate reports)
Secondary targets: Direct company IR websites, CDP portal, SEC EDGAR

Features:
- Playwright-based headless browser automation
- robots.txt compliance
- Rate limiting and retry logic
- Checksum-based deduplication
- Metadata extraction and provenance tracking
- Progress persistence (resume interrupted crawls)

Author: SCA Protocol v13.8-MEA
Date: 2025-10-22
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from libs.utils.clock import get_clock
clock = get_clock()

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import requests  # @allow-network:Crawler requires HTTP access to download ESG reports
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CrawlTarget:
    """Definition of a company/report to crawl"""
    company_name: str
    target_year: Optional[int] = None
    search_terms: Optional[List[str]] = None  # e.g., ["sustainability report", "ESG report"]
    direct_url: Optional[str] = None  # If known, skip search
    priority: int = 1  # 1=high, 5=low


@dataclass
class DownloadedReport:
    """Metadata for a successfully downloaded report"""
    company_name: str
    year: int
    report_type: str  # "sustainability", "esg", "climate", "10-k"
    file_path: str
    source_url: str
    download_date: str
    sha256: str
    size_bytes: int
    crawler_version: str = "1.0.0"
    provenance: str = ""


class SustainabilityReportsCrawler:
    """
    Automated crawler for sustainability/ESG reports.

    Primary mode: Search-based crawling of SustainabilityReports.com
    Fallback mode: Direct URL crawling for known report locations
    """

    def __init__(
        self,
        download_dir: str = "data/pdf_cache",
        metadata_file: str = "data/crawl_metadata.json",
        rate_limit_seconds: float = 2.0,
        max_retries: int = 3,
        user_agent: str = "ESG-Crawler/1.0 (Research; +https://github.com/yourorg/esg-crawler)"
    ):
        """
        Initialize crawler

        Args:
            download_dir: Directory to save downloaded PDFs
            metadata_file: JSON file to track downloaded reports
            rate_limit_seconds: Minimum seconds between requests
            max_retries: Maximum retry attempts per download
            user_agent: User agent string for requests
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = Path(metadata_file)
        self.rate_limit = rate_limit_seconds
        self.max_retries = max_retries
        self.user_agent = user_agent

        # Load existing metadata (resume capability)
        self.downloaded_reports: Dict[str, DownloadedReport] = {}
        self._load_metadata()

        # Track URLs seen (deduplication)
        self.seen_urls: Set[str] = set()

        # robots.txt parsers cache
        self.robots_cache: Dict[str, RobotFileParser] = {}

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not installed. Install with: pip install playwright && playwright install")

    def _load_metadata(self) -> None:
        """Load existing crawl metadata for resume capability"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get('reports', []):
                        report = DownloadedReport(**item)
                        key = f"{report.company_name}_{report.year}_{report.report_type}"
                        self.downloaded_reports[key] = report
                        self.seen_urls.add(report.source_url)
                logger.info(f"Loaded {len(self.downloaded_reports)} existing reports from metadata")
            except Exception as e:
                logger.warning(f"Failed to load metadata: {e}")

    def _save_metadata(self) -> None:
        """Save crawl metadata to disk"""
        metadata = {
            "last_updated": datetime.utcnow().isoformat(),
            "total_reports": len(self.downloaded_reports),
            "reports": [asdict(r) for r in self.downloaded_reports.values()]
        }

        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved metadata: {len(self.downloaded_reports)} reports")

    def _check_robots_txt(self, url: str) -> bool:
        """
        Check if crawling is allowed per robots.txt

        Args:
            url: Target URL to check

        Returns:
            True if allowed, False if disallowed
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url not in self.robots_cache:
            rp = RobotFileParser()
            robots_url = urljoin(base_url, "/robots.txt")
            try:
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[base_url] = rp
                logger.debug(f"Loaded robots.txt from {robots_url}")
            except Exception as e:
                logger.warning(f"Could not load robots.txt from {robots_url}: {e}")
                # Conservative: allow if robots.txt unavailable
                return True

        rp = self.robots_cache[base_url]
        allowed = rp.can_fetch(self.user_agent, url)

        if not allowed:
            logger.warning(f"robots.txt disallows crawling: {url}")

        return allowed

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _extract_year_from_url(self, url: str) -> Optional[int]:
        """Extract year from URL (e.g., /2023-sustainability-report.pdf -> 2023)"""
        matches = re.findall(r'20\d{2}', url)
        if matches:
            # Return most recent year found
            years = [int(y) for y in matches]
            return max(years)
        return None

    def _extract_year_from_text(self, text: str) -> Optional[int]:
        """Extract year from page text"""
        # Look for patterns like "2023 Report", "Fiscal Year 2023", etc.
        patterns = [
            r'(?:fiscal year|FY)\s*(20\d{2})',
            r'(20\d{2})\s*(?:sustainability|ESG|environmental)\s*report',
            r'report.*?(20\d{2})'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                years = [int(y) for y in matches]
                return max(years)  # Most recent

        return None

    def _download_pdf_direct(
        self,
        pdf_url: str,
        company_name: str,
        year: Optional[int] = None,
        report_type: str = "sustainability"
    ) -> Optional[DownloadedReport]:
        """
        Download PDF using requests library (simpler, more reliable for direct URLs)

        Args:
            pdf_url: Direct URL to PDF
            company_name: Company name
            year: Report year
            report_type: Type of report

        Returns:
            DownloadedReport metadata or None if failed
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests library not available. Install with: pip install requests")
            return None

        # Check if already downloaded
        if pdf_url in self.seen_urls:
            logger.info(f"Skipping already downloaded: {pdf_url}")
            return None

        # Extract year if not provided
        if year is None:
            year = self._extract_year_from_url(pdf_url)

        if year is None:
            logger.warning(f"Could not determine year for {pdf_url}, defaulting to current year")
            year = clock.now().year

        # Check deduplication
        key = f"{company_name}_{year}_{report_type}"
        if key in self.downloaded_reports:
            logger.info(f"Already have report for {company_name} {year} ({report_type})")
            return None

        # Generate filename
        safe_name = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        filename = f"{safe_name}_{year}_{report_type}.pdf"
        file_path = self.download_dir / filename

        # Download with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {pdf_url} (attempt {attempt + 1}/{self.max_retries})")

                # Download using requests
                response = requests.get(
                    pdf_url,
                    headers={'User-Agent': self.user_agent},
                    timeout=60,
                    stream=True
                )
                response.raise_for_status()

                # Save to file
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Verify download
                if not file_path.exists() or file_path.stat().st_size == 0:
                    raise Exception("Downloaded file is empty or doesn't exist")

                # Compute checksum
                sha256 = self._compute_sha256(file_path)
                size_bytes = file_path.stat().st_size

                # Create metadata
                report = DownloadedReport(
                    company_name=company_name,
                    year=year,
                    report_type=report_type,
                    file_path=str(file_path),
                    source_url=pdf_url,
                    download_date=datetime.utcnow().isoformat(),
                    sha256=sha256,
                    size_bytes=size_bytes,
                    provenance=f"Crawled from {urlparse(pdf_url).netloc}"
                )

                # Update tracking
                self.downloaded_reports[key] = report
                self.seen_urls.add(pdf_url)
                self._save_metadata()

                logger.info(f"✓ Downloaded: {company_name} {year} ({size_bytes / 1024 / 1024:.2f} MB)")

                # Rate limiting
                time.sleep(self.rate_limit)

                return report

            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.rate_limit * 2)
                else:
                    logger.error(f"Failed to download {pdf_url} after {self.max_retries} attempts")
                    return None

        return None

    async def _download_pdf(
        self,
        page: Page,
        pdf_url: str,
        company_name: str,
        year: Optional[int] = None,
        report_type: str = "sustainability"
    ) -> Optional[DownloadedReport]:
        """
        Download a PDF report

        Args:
            page: Playwright page instance
            pdf_url: Direct URL to PDF
            company_name: Company name
            year: Report year (will attempt to extract if None)
            report_type: Type of report

        Returns:
            DownloadedReport metadata or None if failed
        """
        # Check if already downloaded (deduplication)
        if pdf_url in self.seen_urls:
            logger.info(f"Skipping already downloaded: {pdf_url}")
            return None

        # Extract year if not provided
        if year is None:
            year = self._extract_year_from_url(pdf_url)

        if year is None:
            logger.warning(f"Could not determine year for {pdf_url}, defaulting to current year")
            year = clock.now().year

        # Check deduplication by company+year+type
        key = f"{company_name}_{year}_{report_type}"
        if key in self.downloaded_reports:
            logger.info(f"Already have report for {company_name} {year} ({report_type})")
            return None

        # Generate filename
        safe_name = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        filename = f"{safe_name}_{year}_{report_type}.pdf"
        file_path = self.download_dir / filename

        # Download with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {pdf_url} (attempt {attempt + 1}/{self.max_retries})")

                # Use Playwright's download capability
                # When navigating directly to a PDF, Playwright auto-triggers download
                download_promise = page.wait_for_event('download')
                await page.goto(pdf_url, wait_until='commit', timeout=60000)
                download = await download_promise

                # Save to target path
                await download.save_as(file_path)

                # Verify it's a PDF
                if not file_path.exists() or file_path.stat().st_size == 0:
                    raise Exception("Downloaded file is empty or doesn't exist")

                # Compute checksum
                sha256 = self._compute_sha256(file_path)
                size_bytes = file_path.stat().st_size

                # Create metadata
                report = DownloadedReport(
                    company_name=company_name,
                    year=year,
                    report_type=report_type,
                    file_path=str(file_path),
                    source_url=pdf_url,
                    download_date=datetime.utcnow().isoformat(),
                    sha256=sha256,
                    size_bytes=size_bytes,
                    provenance=f"Crawled from {urlparse(pdf_url).netloc}"
                )

                # Update tracking
                self.downloaded_reports[key] = report
                self.seen_urls.add(pdf_url)
                self._save_metadata()

                logger.info(f"✓ Downloaded: {company_name} {year} ({size_bytes / 1024 / 1024:.2f} MB)")

                # Rate limiting
                await asyncio.sleep(self.rate_limit)

                return report

            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.rate_limit * 2)  # Longer wait on retry
                else:
                    logger.error(f"Failed to download {pdf_url} after {self.max_retries} attempts")
                    return None

        return None

    def crawl_direct_urls_sync(
        self,
        targets: List[Dict[str, any]]
    ) -> List[DownloadedReport]:
        """
        Crawl reports from direct URLs (synchronous, using requests)

        Args:
            targets: List of dicts with keys: company_name, url, year (optional), report_type (optional)

        Returns:
            List of successfully downloaded reports
        """
        downloaded = []

        for target in targets:
            url = target['url']
            company = target['company_name']
            year = target.get('year')
            report_type = target.get('report_type', 'sustainability')

            # Check robots.txt
            if not self._check_robots_txt(url):
                logger.warning(f"Skipping {url} (disallowed by robots.txt)")
                continue

            # Download
            report = self._download_pdf_direct(url, company, year, report_type)
            if report:
                downloaded.append(report)

        logger.info(f"Direct URL crawl complete: {len(downloaded)} reports downloaded")
        return downloaded

    async def crawl_direct_urls(
        self,
        targets: List[Dict[str, any]]
    ) -> List[DownloadedReport]:
        """
        Crawl reports from direct URLs (fastest method when URLs are known)

        DEPRECATED: Use crawl_direct_urls_sync() for direct PDF downloads.
        This async version is kept for backward compatibility.

        Args:
            targets: List of dicts with keys: company_name, url, year (optional), report_type (optional)

        Returns:
            List of successfully downloaded reports
        """
        # Delegate to synchronous version (simpler and more reliable for direct URLs)
        return self.crawl_direct_urls_sync(targets)

    async def search_and_crawl_company(
        self,
        company_name: str,
        target_year: Optional[int] = None,
        report_types: List[str] = None
    ) -> List[DownloadedReport]:
        """
        Search for and download reports for a specific company.

        Uses SustainabilityReports.com search functionality.

        Args:
            company_name: Company name to search for
            target_year: Specific year to target (None = most recent)
            report_types: Types of reports to search for (default: ["sustainability", "esg"])

        Returns:
            List of successfully downloaded reports
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return []

        if report_types is None:
            report_types = ["sustainability", "esg"]

        downloaded = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()

            # Navigate to SustainabilityReports.com search
            search_url = "https://www.sustainabilityreports.com"

            if not self._check_robots_txt(search_url):
                logger.error(f"SustainabilityReports.com disallows crawling")
                await browser.close()
                return []

            try:
                await page.goto(search_url, timeout=30000)
                logger.info(f"Searching for {company_name} reports...")

                # TODO: Implement search logic specific to SustainabilityReports.com structure
                # This is a placeholder - actual implementation depends on site structure

                # Example search flow:
                # 1. Fill search box with company name
                # 2. Submit search
                # 3. Parse results page for PDF links
                # 4. Filter by year if specified
                # 5. Download matching PDFs

                logger.warning("Search functionality not yet implemented - use crawl_direct_urls() instead")

            except Exception as e:
                logger.error(f"Search failed for {company_name}: {e}")

            await browser.close()

        return downloaded

    def get_downloaded_report(self, company_name: str, year: int, report_type: str = "sustainability") -> Optional[DownloadedReport]:
        """Get metadata for a downloaded report"""
        key = f"{company_name}_{year}_{report_type}"
        return self.downloaded_reports.get(key)

    def list_downloaded_reports(self) -> List[DownloadedReport]:
        """List all downloaded reports"""
        return list(self.downloaded_reports.values())
