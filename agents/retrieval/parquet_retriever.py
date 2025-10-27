"""
Parquet Retriever (Structured SQL Queries Over Silver Layer)

Retrieves evidence from silver Parquet files using DuckDB queries.
Supports question-type-specific filtering and confidence ranking.

Part of Task 008 - ESG Data Extraction vertical slice (Option 1).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
import time
import duckdb

from agents.query.query_parser import QueryIntent, QuestionType
from libs.utils.clock import get_clock
clock = get_clock()


@dataclass
class RetrievalResult:
    """
    Result of evidence retrieval operation.

    Attributes:
        query_intent: Original query intent
        evidence: List of evidence records (as dicts)
        total_results: Total number of results found
        retrieval_time_seconds: Time taken for retrieval
    """
    query_intent: QueryIntent
    evidence: List[Dict[str, Any]]
    total_results: int
    retrieval_time_seconds: float


class ParquetRetriever:
    """
    Retrieve evidence from silver Parquet layer using SQL queries.

    Uses DuckDB to query silver layer with filters based on query intent.
    """

    def __init__(self, db_path: Path, bronze_path: Path, silver_path: Path):
        """
        Initialize Parquet retriever.

        Args:
            db_path: Path to DuckDB database
            bronze_path: Path to bronze Parquet directory (for reference)
            silver_path: Path to silver Parquet directory
        """
        self.db_path = Path(db_path)
        self.bronze_path = Path(bronze_path)
        self.silver_path = Path(silver_path)
        self.silver_path.mkdir(parents=True, exist_ok=True)

    def retrieve(
        self,
        intent: QueryIntent,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> RetrievalResult:
        """
        Retrieve evidence based on query intent.

        Args:
            intent: Parsed query intent
            min_confidence: Minimum adjusted_confidence threshold
            limit: Maximum number of results to return

        Returns:
            RetrievalResult with evidence and metadata
        """
        start_time = clock.time()

        con = duckdb.connect(str(self.db_path))

        try:
            # Create silver view
            silver_pattern = str(self.silver_path / "**" / "*.parquet")

            try:
                con.execute(f"""
                    CREATE OR REPLACE TEMP VIEW silver_evidence AS
                    SELECT * FROM read_parquet(
                        '{silver_pattern}',
                        hive_partitioning = true,
                        union_by_name = true
                    )
                """)
            except Exception as e:
                if "No files found" in str(e):
                    # No silver data - return empty result
                    return RetrievalResult(
                        query_intent=intent,
                        evidence=[],
                        total_results=0,
                        retrieval_time_seconds=clock.time() - start_time
                    )
                raise

            # Build query based on intent
            query = self._build_query(intent, min_confidence, limit)

            # Execute query
            df = con.execute(query, [
                intent.company,
                intent.year,
                intent.theme,
                min_confidence
            ]).fetchdf()

            # Convert to list of dicts
            evidence = df.to_dict('records')

            retrieval_time = clock.time() - start_time

            return RetrievalResult(
                query_intent=intent,
                evidence=evidence,
                total_results=len(evidence),
                retrieval_time_seconds=retrieval_time
            )

        finally:
            con.close()

    def _build_query(
        self,
        intent: QueryIntent,
        min_confidence: float,
        limit: int
    ) -> str:
        """
        Build SQL query based on query intent.

        Args:
            intent: Query intent
            min_confidence: Minimum confidence threshold
            limit: Result limit

        Returns:
            SQL query string
        """
        # Base query
        query = f"""
            SELECT
                evidence_id,
                org_id,
                year,
                theme,
                stage_indicator,
                doc_id,
                page_no,
                span_start,
                span_end,
                extract_30w,
                hash_sha256,
                confidence,
                evidence_type,
                is_most_recent,
                freshness_penalty,
                adjusted_confidence
            FROM silver_evidence
            WHERE org_id = ?
              AND year = ?
              AND theme = ?
              AND adjusted_confidence >= ?
              AND is_most_recent = TRUE
        """

        # Add question-type-specific filters
        question_filter = self._get_question_type_filter(intent.question_type)
        if question_filter:
            query += f" AND {question_filter}"

        # Order by adjusted_confidence DESC
        query += " ORDER BY adjusted_confidence DESC, page_no ASC"

        # Limit results
        query += f" LIMIT {limit}"

        return query

    def _get_question_type_filter(self, question_type: QuestionType) -> str:
        """
        Get SQL filter for specific question types.

        Args:
            question_type: Question type from intent

        Returns:
            SQL WHERE clause fragment (or empty string)
        """
        # Map question types to evidence_type filters
        filters = {
            QuestionType.SCOPE_1_EMISSIONS: "evidence_type LIKE '%scope%1%'",
            QuestionType.SCOPE_2_EMISSIONS: "evidence_type LIKE '%scope%2%'",
            QuestionType.SCOPE_3_DISCLOSURE: "evidence_type LIKE '%scope%3%'",
            QuestionType.SCOPE_12_EMISSIONS: "(evidence_type LIKE '%scope%1%' OR evidence_type LIKE '%scope%2%' OR evidence_type LIKE '%scope_12%')",
            QuestionType.SCOPE_123_COMPREHENSIVE: "(evidence_type LIKE '%scope%' OR evidence_type LIKE '%comprehensive%')",
            QuestionType.EMISSIONS_TARGET: "evidence_type LIKE '%target%'",
            QuestionType.ASSURANCE_LEVEL: "evidence_type LIKE '%assurance%'",
            QuestionType.GENERAL: ""  # No specific filter
        }

        return filters.get(question_type, "")
