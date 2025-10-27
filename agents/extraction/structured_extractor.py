"""
Structured Data Extractor - Phase 3 (Asymmetric Extraction)

Extracts ESG metrics from structured data sources (JSON, XBRL).
Handles SEC EDGAR companyfacts JSON with us-gaap taxonomy mapping.

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from libs.contracts.extraction_contracts import (
    ExtractionError,
    ExtractionQuality,
    ExtractionResult,
)
from libs.contracts.ingestion_contracts import CompanyReport
from libs.models.esg_metrics import ESGMetrics


class StructuredExtractor:
    """Extract ESG metrics from structured data (JSON/XBRL).

    Supports SEC EDGAR companyfacts JSON format with us-gaap taxonomy.
    Maps financial metrics to ESGMetrics Pydantic model.
    """

    # Mapping from us-gaap concepts to ESGMetrics fields
    US_GAAP_FIELD_MAPPING = {
        "Assets": "assets",
        "Liabilities": "liabilities",
        "StockholdersEquity": "stockholders_equity",
        "Revenues": "revenues",
        "NetIncomeLoss": "net_income",
        "OperatingIncomeLoss": "operating_income",
        "CommonStockSharesOutstanding": "shares_outstanding",
    }

    def __init__(self) -> None:
        """Initialize StructuredExtractor."""
        self.errors: List[ExtractionError] = []

    def extract(self, report: CompanyReport) -> ExtractionResult:
        """Extract ESG metrics from structured company report.

        Args:
            report: CompanyReport with local_path to JSON file

        Returns:
            ExtractionResult with metrics, quality, and errors

        Raises:
            FileNotFoundError: If report.local_path does not exist
            ValueError: If report.local_path is None
        """
        self.errors = []  # Reset errors for new extraction

        # Validate input
        if report.local_path is None:
            raise ValueError("CompanyReport.local_path is None")

        local_path = Path(report.local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Report file not found: {local_path}")

        # Read and parse JSON
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(
                ExtractionError(
                    field_name=None,
                    error_type="JSONDecodeError",
                    message=f"Failed to parse JSON: {e}",
                    severity="error",
                )
            )
            return self._create_failed_result()

        # Extract metrics
        metrics = self._extract_metrics_from_sec_edgar(data, report)

        # Calculate quality
        quality = self._calculate_quality(metrics)

        return ExtractionResult(metrics=metrics, quality=quality, errors=self.errors)

    def _extract_metrics_from_sec_edgar(
        self, data: Dict[str, Any], report: CompanyReport
    ) -> Optional[ESGMetrics]:
        """Extract metrics from SEC EDGAR companyfacts JSON.

        Args:
            data: Parsed JSON data from SEC EDGAR
            report: CompanyReport with company metadata

        Returns:
            ESGMetrics instance or None if extraction failed
        """
        try:
            # Extract company info
            entity_name = data.get("entityName", report.company.name)
            cik = str(data.get("cik", report.company.cik)).zfill(10)

            # Extract us-gaap facts
            facts = data.get("facts", {}).get("us-gaap", {})
            if not facts:
                self.errors.append(
                    ExtractionError(
                        field_name=None,
                        error_type="MissingField",
                        message="No us-gaap facts found in SEC EDGAR JSON",
                        severity="error",
                    )
                )
                return None

            # Map us-gaap fields to ESGMetrics
            metrics_dict: Dict[str, Any] = {
                "company_name": entity_name,
                "cik": cik,
                "fiscal_year": report.year,
                "extraction_method": "structured",
                "extraction_timestamp": datetime.utcnow(),
                "data_source": "sec_edgar",
            }

            # Extract financial metrics
            for us_gaap_field, esg_field in self.US_GAAP_FIELD_MAPPING.items():
                value = self._get_latest_value(facts, us_gaap_field, report.year)
                if value is not None:
                    metrics_dict[esg_field] = value
                # NOTE: Missing optional fields are expected and not logged as errors
                # ESGMetrics has Optional[float] for all financial metrics

            # Create ESGMetrics instance
            metrics = ESGMetrics(**metrics_dict)
            return metrics

        except Exception as e:
            self.errors.append(
                ExtractionError(
                    field_name=None,
                    error_type=type(e).__name__,
                    message=f"Failed to extract metrics: {e}",
                    severity="error",
                )
            )
            return None

    def _get_latest_value(
        self, facts: Dict[str, Any], concept: str, target_year: int
    ) -> Optional[float]:
        """Get latest value for a us-gaap concept for target year.

        Args:
            facts: us-gaap facts dictionary
            concept: us-gaap concept name (e.g., "Assets")
            target_year: Target fiscal year

        Returns:
            Latest value for target year or None if not found
        """
        if concept not in facts:
            return None

        concept_data = facts[concept]
        units = concept_data.get("units", {})

        # Try USD first (most common for financial metrics)
        for unit_key in ["USD", "shares", "pure"]:
            if unit_key in units:
                values = units[unit_key]
                # Find values for target year
                candidates = [
                    v
                    for v in values
                    if v.get("fy") == target_year and "val" in v
                ]
                if candidates:
                    # Return most recent value (sorted by filed date)
                    candidates.sort(key=lambda x: x.get("filed", ""), reverse=True)
                    return float(candidates[0]["val"])

        return None

    def _calculate_quality(self, metrics: Optional[ESGMetrics]) -> ExtractionQuality:
        """Calculate quality metrics for extraction.

        Args:
            metrics: Extracted ESGMetrics or None

        Returns:
            ExtractionQuality with completeness, correctness, and validity
        """
        if metrics is None:
            return ExtractionQuality(
                field_completeness=0.0, type_correctness=0.0, value_validity=0.0
            )

        # Calculate field completeness (fraction of non-None fields)
        metrics_dict = metrics.dict()
        total_fields = len(metrics_dict)
        non_none_fields = sum(1 for v in metrics_dict.values() if v is not None)
        field_completeness = non_none_fields / total_fields if total_fields > 0 else 0.0

        # Type correctness is 1.0 (Pydantic guarantees type safety)
        type_correctness = 1.0

        # Value validity (fraction of fields passing Pydantic validation)
        # Since we already created ESGMetrics instance, all values are valid
        value_validity = 1.0

        return ExtractionQuality(
            field_completeness=field_completeness,
            type_correctness=type_correctness,
            value_validity=value_validity,
        )

    def _create_failed_result(self) -> ExtractionResult:
        """Create ExtractionResult for failed extraction."""
        return ExtractionResult(
            metrics=None,
            quality=ExtractionQuality(
                field_completeness=0.0, type_correctness=0.0, value_validity=0.0
            ),
            errors=self.errors,
        )
