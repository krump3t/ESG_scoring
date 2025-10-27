"""
Extraction Router - Phase 3 (Asymmetric Extraction Paths)

Routes extraction requests to appropriate extractors based on content type.
Implements asymmetric extraction: structured (JSON/XBRL) vs unstructured (PDF/HTML).

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24
"""

from typing import Any, Optional

from agents.extraction.structured_extractor import StructuredExtractor
from libs.contracts.extraction_contracts import (
    ExtractionError,
    ExtractionQuality,
    MetricsExtractionResult,
)
from libs.contracts.ingestion_contracts import CompanyReport


class ExtractionRouter:
    """Route extraction requests to appropriate extractors.

    Asymmetric extraction paths:
    - Structured: application/json, application/xml → StructuredExtractor
    - Unstructured: application/pdf, text/html → LLMExtractor (future)
    """

    # Content-type to extractor mapping
    STRUCTURED_CONTENT_TYPES = {
        "application/json",
        "application/xml",
        "application/xbrl+xml",
    }

    UNSTRUCTURED_CONTENT_TYPES = {
        "application/pdf",
        "text/html",
        "text/plain",
    }

    def __init__(self, watsonx_client: Optional[Any] = None) -> None:
        """Initialize ExtractionRouter.

        Args:
            watsonx_client: IBM watsonx.ai client for LLM extraction (optional, for future use)
        """
        self.structured_extractor = StructuredExtractor()
        self.watsonx_client = watsonx_client
        # LLMExtractor will be added in future iteration

    def extract(self, report: CompanyReport) -> MetricsExtractionResult:
        """Extract ESG metrics from company report.

        Routes to appropriate extractor based on report.source.content_type.

        Args:
            report: CompanyReport with source metadata and local file

        Returns:
            MetricsExtractionResult with metrics, quality, and errors

        Raises:
            ValueError: If content_type is unsupported
        """
        content_type = report.source.content_type

        # Route to structured extractor
        if content_type in self.STRUCTURED_CONTENT_TYPES:
            return self.structured_extractor.extract(report)

        # Route to LLM extractor (future)
        if content_type in self.UNSTRUCTURED_CONTENT_TYPES:
            return self._extract_unstructured_not_implemented(report, content_type)

        # Unsupported content type
        raise ValueError(
            f"Unsupported content_type: {content_type}. "
            f"Supported: {self.STRUCTURED_CONTENT_TYPES | self.UNSTRUCTURED_CONTENT_TYPES}"
        )

    def _extract_unstructured_not_implemented(
        self, report: CompanyReport, content_type: str
    ) -> MetricsExtractionResult:
        """Placeholder for unstructured extraction (PDF/HTML).

        Will be implemented with IBM watsonx.ai in future iteration.

        Args:
            report: CompanyReport with PDF/HTML file
            content_type: Content type (application/pdf, text/html)

        Returns:
            MetricsExtractionResult with error indicating not implemented
        """
        error = ExtractionError(
            field_name=None,
            error_type="NotImplementedError",
            message=f"Unstructured extraction for {content_type} not yet implemented. "
            f"Requires IBM watsonx.ai integration (planned for future iteration).",
            severity="error",
        )

        return MetricsExtractionResult(
            metrics=None,
            quality=ExtractionQuality(
                field_completeness=0.0, type_correctness=0.0, value_validity=0.0
            ),
            errors=[error],
        )

    def supports_content_type(self, content_type: str) -> bool:
        """Check if content type is supported.

        Args:
            content_type: MIME type (e.g., "application/json")

        Returns:
            True if content type is supported
        """
        return content_type in (
            self.STRUCTURED_CONTENT_TYPES | self.UNSTRUCTURED_CONTENT_TYPES
        )

    def get_extractor_type(self, content_type: str) -> str:
        """Get extractor type for content type.

        Args:
            content_type: MIME type

        Returns:
            "structured", "unstructured", or "unsupported"
        """
        if content_type in self.STRUCTURED_CONTENT_TYPES:
            return "structured"
        if content_type in self.UNSTRUCTURED_CONTENT_TYPES:
            return "unstructured"
        return "unsupported"
