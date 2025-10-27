"""
Query Orchestrator (Trigger Ingestion on Cache Miss)

Coordinates the data ingestion pipeline:
1. Check cache status
2. If cache miss: trigger ingestion
   a. Fetch SEC filing (from cache or SEC EDGAR API)
   b. Parse HTML
   c. Extract evidence
   d. Write to bronze
   e. Normalize to silver
3. Track ingestion job status

Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import time

from agents.query.query_parser import QueryIntent
from agents.query.cache_manager import CacheManager, CacheStatus
from agents.parser.evidence_extractor import EvidenceExtractor
from agents.parser.matchers.ghg_matcher import GHGMatcher
from agents.storage.bronze_writer import BronzeEvidenceWriter
from agents.storage.silver_normalizer import SilverNormalizer


class IngestionStatus(Enum):
    """Status of ingestion job"""
    CACHE_HIT = "cache_hit"          # Data already in cache
    IN_PROGRESS = "in_progress"      # Currently ingesting
    COMPLETED = "completed"          # Successfully completed
    FAILED = "failed"                # Failed with error


@dataclass
class IngestionJob:
    """
    Result of data ingestion operation.

    Attributes:
        company: Company ticker
        year: Fiscal year
        theme: ESG theme
        status: Ingestion status
        cache_status: Initial cache status
        records_ingested: Number of records ingested (0 if cache hit)
        processing_time_seconds: Time taken for ingestion
        error_message: Error message if failed
    """
    company: str
    year: int
    theme: str
    status: IngestionStatus
    cache_status: CacheStatus
    records_ingested: int
    processing_time_seconds: float
    error_message: Optional[str] = None


class QueryOrchestrator:
    """
    Orchestrate data ingestion pipeline for query processing.

    Checks cache and triggers ingestion if needed.
    """

    def __init__(
        self,
        bronze_path: Path,
        silver_path: Path,
        cache_path: Path,
        db_path: Path
    ):
        """
        Initialize query orchestrator.

        Args:
            bronze_path: Path to bronze Parquet directory
            silver_path: Path to silver Parquet directory
            cache_path: Path to cached SEC filings
            db_path: Path to DuckDB database
        """
        self.bronze_path = Path(bronze_path)
        self.silver_path = Path(silver_path)
        self.cache_path = Path(cache_path)
        self.db_path = Path(db_path)

        # Ensure directories exist
        self.bronze_path.mkdir(parents=True, exist_ok=True)
        self.silver_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.cache_manager = CacheManager(
            db_path=db_path,
            bronze_path=bronze_path,
            silver_path=silver_path
        )
        self.bronze_writer = BronzeEvidenceWriter(base_path=bronze_path)
        self.silver_normalizer = SilverNormalizer(
            db_path=db_path,
            bronze_path=bronze_path,
            silver_path=silver_path
        )
        self.evidence_extractor = EvidenceExtractor(matchers=[GHGMatcher()])

    def ensure_data_available(
        self,
        intent: QueryIntent,
        use_cached_filing: bool = True
    ) -> IngestionJob:
        """
        Ensure data is available for query intent.

        Checks cache first. If cache miss, triggers ingestion.

        Args:
            intent: Parsed query intent
            use_cached_filing: If True, use cached SEC filing (for testing)
                              If False, fetch from SEC EDGAR API

        Returns:
            IngestionJob with status and metadata
        """
        start_time = time.time()

        # Check cache
        cache_result = self.cache_manager.check_cache(
            company=intent.company,
            year=intent.year,
            theme=intent.theme
        )

        # Cache hit - return immediately
        if cache_result.status == CacheStatus.COMPLETE:
            return IngestionJob(
                company=intent.company,
                year=intent.year,
                theme=intent.theme,
                status=IngestionStatus.CACHE_HIT,
                cache_status=cache_result.status,
                records_ingested=0,
                processing_time_seconds=time.time() - start_time,
                error_message=None
            )

        # Cache miss - trigger ingestion
        try:
            # Step 1: Get SEC filing HTML
            html_content = self._get_sec_filing(
                company=intent.company,
                year=intent.year,
                use_cached=use_cached_filing
            )

            # Step 2: Extract evidence (internally parses HTML)
            extraction_result = self.evidence_extractor.extract_from_html(
                html_content=html_content,
                org_id=intent.company,
                year=intent.year,
                doc_id=f"{intent.company.lower()}-10k-{intent.year}"
            )

            # Flatten evidence from all themes
            all_evidence = []
            for theme_evidence_list in extraction_result.evidence_by_theme.values():
                all_evidence.extend(theme_evidence_list)

            # Step 4: Write to bronze
            if all_evidence:
                ingestion_id = f"orchestrator_{intent.company}_{intent.year}_{int(time.time())}"
                self.bronze_writer.write_evidence_batch(
                    evidence_list=all_evidence,
                    ingestion_id=ingestion_id
                )

                # Step 5: Normalize to silver
                self.silver_normalizer.normalize_bronze_to_silver()

            processing_time = time.time() - start_time

            return IngestionJob(
                company=intent.company,
                year=intent.year,
                theme=intent.theme,
                status=IngestionStatus.COMPLETED,
                cache_status=cache_result.status,
                records_ingested=len(all_evidence),
                processing_time_seconds=processing_time,
                error_message=None
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return IngestionJob(
                company=intent.company,
                year=intent.year,
                theme=intent.theme,
                status=IngestionStatus.FAILED,
                cache_status=cache_result.status,
                records_ingested=0,
                processing_time_seconds=processing_time,
                error_message=str(e)
            )

    def _get_sec_filing(
        self,
        company: str,
        year: int,
        use_cached: bool = True
    ) -> str:
        """
        Get SEC filing HTML content.

        Args:
            company: Company ticker
            year: Fiscal year
            use_cached: If True, look for cached filing first

        Returns:
            HTML content of SEC 10-K filing

        Raises:
            FileNotFoundError: If cached filing not found and use_cached=True
            NotImplementedError: If use_cached=False (SEC EDGAR fetch not yet implemented)
        """
        if use_cached:
            # Look for cached filing
            cached_filing = self.cache_path / f"{company}_10K_{year}.html"
            if not cached_filing.exists():
                raise FileNotFoundError(f"Cached filing not found: {cached_filing}")

            return cached_filing.read_text(encoding='utf-8', errors='ignore')
        else:
            # Fetch from SEC EDGAR API
            # TODO: Implement SEC EDGAR fetch using SEC_EDGAR_Provider
            raise NotImplementedError("SEC EDGAR API fetch not yet implemented")
