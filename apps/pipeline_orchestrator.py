"""
Phase 5: Pipeline Orchestrator

Orchestrates end-to-end pipeline (Phase 2 → Phase 3 → Phase 4) with error handling,
logging, and metrics collection.

Architecture:
  Phase 2 (Crawler) → [CompanyReport]
       ↓
  Phase 3 (Extractor) → [ESGMetrics]
       ↓
  Phase 4 (Writer) → [Parquet file]
       ↓
  Phase 4 (Reader) → [Query results]
       ↓
  IntegrationValidator → [Validation report]

Execution:
- Sequential (no parallelism)
- Fail-fast on critical errors
- Log-and-continue on warnings
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from libs.utils.clock import get_clock
clock = get_clock()

from agents.crawler.multi_source_crawler_v2 import MultiSourceCrawler
from agents.extraction.extraction_router import ExtractionRouter
from libs.models.esg_metrics import ESGMetrics
from libs.data_lake.parquet_writer import ParquetWriter
from libs.data_lake.duckdb_reader import DuckDBReader


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    success: bool
    company_name: str
    cik: str
    fiscal_year: int
    error: Optional[str] = None
    error_phase: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    latencies: Dict[str, float] = field(default_factory=dict)
    total_latency: float = 0.0
    parquet_file: Optional[Path] = None

    def __str__(self) -> str:
        """String representation of pipeline result."""
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"PipelineResult({status}): {self.company_name} (CIK {self.cik}, FY{self.fiscal_year})\n"
            f"  Total latency: {self.total_latency:.2f}s\n"
            f"  Phase latencies: {self.latencies}\n"
        )


class PipelineError(Exception):
    """Raised when pipeline encounters critical error."""

    def __init__(self, message: str, phase: str):
        self.message = message
        self.phase = phase
        super().__init__(f"[{phase}] {message}")


# ============================================================================
# Orchestrator
# ============================================================================

class PipelineOrchestrator:
    """Orchestrates end-to-end ESG data pipeline."""

    def __init__(self, project_config: Dict[str, Any]):
        """Initialize orchestrator with Phase 2-4 components.

        Args:
            project_config: Configuration dict with API keys, paths, rate limits.

        Raises:
            ValueError: If config is missing required keys.
        """
        if not project_config:
            raise ValueError("project_config cannot be None")

        self.project_config = project_config
        # Note: MultiSourceCrawler requires provider tiers; this is a placeholder
        # In real usage, Phase 2 would initialize with proper provider configuration
        self.crawler = None  # TODO: Initialize with Phase 2 providers
        self.extractor = ExtractionRouter(project_config)
        self.writer = ParquetWriter(
            base_path=project_config.get("paths", {}).get("data_lake", "data_lake/")
        )
        self.reader = DuckDBReader(
            base_path=project_config.get("paths", {}).get("data_lake", "data_lake/")
        )

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging to both file and console."""
        log_dir = Path(self.project_config.get("paths", {}).get("logs", "qa/"))
        log_dir.mkdir(parents=True, exist_ok=True)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler
        log_file = log_dir / f"pipeline_{clock.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)

    def run_pipeline(
        self,
        company_cik: str,
        fiscal_year: int,
    ) -> PipelineResult:
        """Execute complete pipeline for one company.

        Orchestrates Phase 2 (crawl) → Phase 3 (extract) → Phase 4 (write/query)
        with error handling and metrics collection.

        Args:
            company_cik: SEC CIK (e.g., "0000789019" for Microsoft)
            fiscal_year: Fiscal year (e.g., 2024)

        Returns:
            PipelineResult with success flag, metrics, latencies

        Raises:
            PipelineError: If critical error occurs (fail-fast)
        """
        start_time = clock.time()

        self.logger.info(f"Pipeline start: CIK={company_cik}, Year={fiscal_year}")

        try:
            # Phase 2: Crawl
            report = self._phase2_crawl(company_cik, fiscal_year)
            company_name = report.get("company_name", "Unknown")

            # Phase 3: Extract
            metrics = self._phase3_extract(report)

            # Phase 4: Write
            parquet_file = self._phase4_write(metrics, company_cik, fiscal_year)

            # Phase 4: Query
            queried_metrics = self._phase4_query(company_name, parquet_file.name)

            # Calculate total latency
            total_latency = clock.time() - start_time

            result = PipelineResult(
                success=True,
                company_name=company_name,
                cik=company_cik,
                fiscal_year=fiscal_year,
                metrics={
                    "assets": queried_metrics.assets,
                    "liabilities": queried_metrics.liabilities,
                    "net_income": queried_metrics.net_income,
                },
                latencies=getattr(self, "_latencies", {}),
                total_latency=total_latency,
                parquet_file=parquet_file,
            )

            self.logger.info(f"Pipeline complete: {total_latency:.2f}s")
            return result

        except PipelineError as e:
            self.logger.error(f"Pipeline failed in {e.phase}: {e.message}")
            total_latency = clock.time() - start_time

            return PipelineResult(
                success=False,
                company_name="Unknown",
                cik=company_cik,
                fiscal_year=fiscal_year,
                error=e.message,
                error_phase=e.phase,
                total_latency=total_latency,
            )

    def _phase2_crawl(self, company_cik: str, fiscal_year: int) -> Dict[str, Any]:
        """Phase 2: Crawl SEC EDGAR for company report.

        Args:
            company_cik: SEC CIK code
            fiscal_year: Fiscal year

        Returns:
            Report dict with content, source, timestamp, sha256

        Raises:
            PipelineError: If crawler fails
        """
        phase_start = clock.time()

        try:
            self.logger.debug(f"Phase 2: Crawling CIK={company_cik}, FY={fiscal_year}")

            report = self.crawler.crawl_company(company_cik, fiscal_year)

            if report is None or not report.get("content"):
                raise PipelineError("Crawler returned empty report", "Phase 2")

            phase_latency = clock.time() - phase_start
            self.logger.info(f"Phase 2 complete: crawled in {phase_latency:.2f}s")

            if not hasattr(self, "_latencies"):
                self._latencies = {}
            self._latencies["phase2"] = phase_latency

            return report

        except Exception as e:
            if isinstance(e, PipelineError):
                raise
            raise PipelineError(f"Crawler error: {str(e)}", "Phase 2")

    def _phase3_extract(self, report: Dict[str, Any]) -> ESGMetrics:
        """Phase 3: Extract metrics from report.

        Args:
            report: CompanyReport dict from Phase 2

        Returns:
            ESGMetrics instance

        Raises:
            PipelineError: If extraction fails
        """
        phase_start = clock.time()

        try:
            self.logger.debug("Phase 3: Extracting metrics")

            metrics = self.extractor.extract(report)

            if not isinstance(metrics, ESGMetrics):
                raise PipelineError("Extractor did not return ESGMetrics", "Phase 3")

            phase_latency = clock.time() - phase_start
            self.logger.info(f"Phase 3 complete: extracted in {phase_latency:.2f}s")

            if not hasattr(self, "_latencies"):
                self._latencies = {}
            self._latencies["phase3"] = phase_latency

            return metrics

        except Exception as e:
            if isinstance(e, PipelineError):
                raise
            raise PipelineError(f"Extraction error: {str(e)}", "Phase 3")

    def _phase4_write(
        self,
        metrics: ESGMetrics,
        company_cik: str,
        fiscal_year: int
    ) -> Path:
        """Phase 4: Write metrics to Parquet file.

        Args:
            metrics: ESGMetrics from Phase 3
            company_cik: SEC CIK code
            fiscal_year: Fiscal year

        Returns:
            Path to written Parquet file

        Raises:
            PipelineError: If write fails
        """
        phase_start = clock.time()

        try:
            filename = f"{metrics.company_name.lower().replace(' ', '_')}_{company_cik}_{fiscal_year}.parquet"
            self.logger.debug(f"Phase 4 Write: Writing to {filename}")

            self.writer.write_metrics(metrics, filename)

            parquet_file = Path(self.writer.base_path) / filename

            if not parquet_file.exists():
                raise PipelineError(f"Parquet file not created: {filename}", "Phase 4 Write")

            phase_latency = clock.time() - phase_start
            self.logger.info(f"Phase 4 Write complete: written in {phase_latency:.2f}s")

            if not hasattr(self, "_latencies"):
                self._latencies = {}
            self._latencies["phase4_write"] = phase_latency

            return parquet_file

        except Exception as e:
            if isinstance(e, PipelineError):
                raise
            raise PipelineError(f"Write error: {str(e)}", "Phase 4 Write")

    def _phase4_query(self, company_name: str, filename: str) -> ESGMetrics:
        """Phase 4: Query metrics from data lake.

        Args:
            company_name: Company name for query
            filename: Parquet filename to query

        Returns:
            ESGMetrics retrieved from DuckDB

        Raises:
            PipelineError: If query fails
        """
        phase_start = clock.time()

        try:
            self.logger.debug(f"Phase 4 Query: Querying {company_name} from {filename}")

            metrics = self.reader.get_latest_metrics(company_name, filename)

            if metrics is None:
                raise PipelineError(f"Query returned no results for {company_name}", "Phase 4 Query")

            phase_latency = clock.time() - phase_start
            self.logger.info(f"Phase 4 Query complete: queried in {phase_latency:.2f}s")

            if not hasattr(self, "_latencies"):
                self._latencies = {}
            self._latencies["phase4_query"] = phase_latency

            return metrics

        except Exception as e:
            if isinstance(e, PipelineError):
                raise
            raise PipelineError(f"Query error: {str(e)}", "Phase 4 Query")
