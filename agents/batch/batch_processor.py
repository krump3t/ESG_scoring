"""
Batch Processor for Multi-Company Evidence Extraction

Orchestrates complete pipeline for multiple companies:
1. Load SEC filing HTML (from cache or fetch)
2. Extract evidence using matchers
3. Write to bronze layer (Parquet)
4. Normalize to silver layer (optional)
5. Track progress and handle errors

Implements batch processing with progress tracking and error handling.
Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
import time

from agents.parser.evidence_extractor import EvidenceExtractor
from agents.parser.matchers.ghg_matcher import GHGMatcher
from agents.storage.bronze_writer import BronzeEvidenceWriter
from agents.storage.silver_normalizer import SilverNormalizer
from libs.utils.clock import get_clock
clock = get_clock()


@dataclass
class CompanyProcessingResult:
    """Result of processing a single company"""
    ticker: str
    year: int
    success: bool
    evidence_count: int
    processing_time_seconds: float
    error_message: Optional[str] = None


@dataclass
class BatchProcessingResult:
    """Result of processing a batch of companies"""
    batch_id: str
    total_companies: int
    successful_companies: int
    failed_companies: int
    total_evidence_extracted: int
    processing_time_seconds: float
    company_results: List[CompanyProcessingResult]


class BatchProcessor:
    """
    Batch processor for multi-company evidence extraction.

    Orchestrates complete pipeline from SEC filing to silver layer.
    Provides progress tracking, error handling, and summary statistics.
    """

    def __init__(
        self,
        bronze_path: Path,
        silver_path: Path,
        db_path: Path,
        cache_path: Path
    ):
        """
        Initialize batch processor.

        Args:
            bronze_path: Path to bronze Parquet directory
            silver_path: Path to silver Parquet directory
            db_path: Path to DuckDB database file
            cache_path: Path to cached SEC filings directory
        """
        self.bronze_path = Path(bronze_path)
        self.silver_path = Path(silver_path)
        self.db_path = Path(db_path)
        self.cache_path = Path(cache_path)

        # Ensure directories exist
        self.bronze_path.mkdir(parents=True, exist_ok=True)
        self.silver_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.extractor = EvidenceExtractor(matchers=[GHGMatcher()])
        self.bronze_writer = BronzeEvidenceWriter(base_path=self.bronze_path)
        self.silver_normalizer = SilverNormalizer(
            db_path=self.db_path,
            bronze_path=self.bronze_path,
            silver_path=self.silver_path
        )

    def process_company(
        self,
        ticker: str,
        year: int,
        filing_path: Path,
        normalize: bool = False
    ) -> CompanyProcessingResult:
        """
        Process a single company through the evidence extraction pipeline.

        Args:
            ticker: Company ticker symbol (e.g., "MSFT")
            year: Fiscal year (e.g., 2023)
            filing_path: Path to SEC filing HTML file
            normalize: Whether to normalize to silver layer after extraction

        Returns:
            CompanyProcessingResult with processing statistics
        """
        start_time = clock.time()

        try:
            # Check if filing exists
            if not filing_path.exists():
                return CompanyProcessingResult(
                    ticker=ticker,
                    year=year,
                    success=False,
                    evidence_count=0,
                    processing_time_seconds=clock.time() - start_time,
                    error_message=f"Filing not found: {filing_path}"
                )

            # Read HTML content
            html_content = filing_path.read_text(encoding='utf-8', errors='ignore')

            # Extract evidence
            extraction_result = self.extractor.extract_from_html(
                html_content=html_content,
                org_id=ticker,
                year=year,
                doc_id=f"{ticker.lower()}-10k-{year}"
            )

            # Flatten evidence from all themes
            all_evidence = []
            for theme_evidence_list in extraction_result.evidence_by_theme.values():
                all_evidence.extend(theme_evidence_list)

            # Generate ingestion ID
            ingestion_id = f"batch_{ticker}_{year}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

            # Write to bronze layer
            if all_evidence:
                self.bronze_writer.write_evidence_batch(
                    evidence_list=all_evidence,
                    ingestion_id=ingestion_id
                )

            # Normalize to silver if requested
            if normalize and all_evidence:
                self.silver_normalizer.normalize_bronze_to_silver()

            processing_time = clock.time() - start_time

            return CompanyProcessingResult(
                ticker=ticker,
                year=year,
                success=True,
                evidence_count=len(all_evidence),
                processing_time_seconds=processing_time,
                error_message=None
            )

        except Exception as e:
            processing_time = clock.time() - start_time
            return CompanyProcessingResult(
                ticker=ticker,
                year=year,
                success=False,
                evidence_count=0,
                processing_time_seconds=processing_time,
                error_message=str(e)
            )

    def process_batch(
        self,
        companies: List[Dict[str, Any]],
        normalize: bool = True
    ) -> BatchProcessingResult:
        """
        Process a batch of companies through the evidence extraction pipeline.

        Args:
            companies: List of company dicts with keys: ticker, year, filing_path
            normalize: Whether to normalize to silver layer after all extractions

        Returns:
            BatchProcessingResult with batch statistics
        """
        start_time = clock.time()
        batch_id = f"batch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"

        company_results: List[CompanyProcessingResult] = []
        total_evidence = 0

        # Process each company
        for company in companies:
            result = self.process_company(
                ticker=company['ticker'],
                year=company['year'],
                filing_path=company['filing_path'],
                normalize=False  # Normalize once at the end
            )
            company_results.append(result)
            if result.success:
                total_evidence += result.evidence_count

        # Normalize to silver once at the end (if requested)
        if normalize and total_evidence > 0:
            self.silver_normalizer.normalize_bronze_to_silver()

        # Calculate summary statistics
        processing_time = clock.time() - start_time
        successful = sum(1 for r in company_results if r.success)
        failed = len(company_results) - successful

        return BatchProcessingResult(
            batch_id=batch_id,
            total_companies=len(companies),
            successful_companies=successful,
            failed_companies=failed,
            total_evidence_extracted=total_evidence,
            processing_time_seconds=processing_time,
            company_results=company_results
        )
