"""
Evidence Extraction Pipeline

Orchestrates HTML parsing and evidence matching for ESG maturity assessment.
Connects SEC filing HTML → Parser → Matchers → Evidence objects.

Part of Option 1 (GHG Vertical Slice) for validating end-to-end pipeline.
"""

from typing import List, Dict, Optional
from pathlib import Path
import logging
from datetime import datetime
import hashlib

from .html_parser import SECHTMLParser
from .models import Evidence, Match, EvidenceExtractionResult
from .matchers.base_matcher import BaseMatcher
from .matchers.ghg_matcher import GHGMatcher

logger = logging.getLogger(__name__)


class EvidenceExtractor:
    """
    Extract ESG evidence from SEC filings using theme-specific matchers.

    Coordinates:
    1. HTML parsing (SEC 10-K structure)
    2. Pattern matching (GHG, TSP, OSP, etc.)
    3. Evidence object creation with citations
    4. Result aggregation
    """

    def __init__(self, matchers: Optional[List[BaseMatcher]] = None):
        """
        Initialize evidence extractor.

        Args:
            matchers: List of theme matchers. If None, uses GHG matcher only (Option 1).
        """
        self.html_parser = SECHTMLParser()

        # Default to GHG matcher for vertical slice (Option 1)
        if matchers is None:
            self.matchers = [GHGMatcher()]
            logger.info("EvidenceExtractor initialized with GHG matcher (vertical slice)")
        else:
            self.matchers = matchers
            themes = [m.theme for m in matchers]
            logger.info(f"EvidenceExtractor initialized with {len(matchers)} matchers: {themes}")

    def extract_from_html(
        self,
        html_content: str,
        org_id: str,
        year: int,
        doc_id: str,
        filing_url: str = ""
    ) -> EvidenceExtractionResult:
        """
        Extract evidence from SEC filing HTML.

        Args:
            html_content: Raw HTML from SEC EDGAR
            org_id: Organization identifier (e.g., CIK or ticker)
            year: Fiscal year of the filing
            doc_id: Document identifier (e.g., accession number)
            filing_url: URL to original filing (for traceability)

        Returns:
            ExtractionResult with all extracted evidence by theme
        """
        logger.info(f"Extracting evidence for {org_id} ({year}) from doc {doc_id}")

        # Step 1: Parse HTML
        document_text, page_offsets = self.html_parser.parse_filing(html_content, filing_url)
        logger.debug(f"Parsed {len(document_text)} characters, {len(page_offsets)} pages")

        # Step 2: Run matchers
        evidence_by_theme: Dict[str, List[Evidence]] = {}
        total_matches = 0

        for matcher in self.matchers:
            theme = matcher.theme
            logger.debug(f"Running {theme} matcher...")

            # Get matches from matcher
            matches = matcher.match(document_text, page_offsets)
            logger.debug(f"{theme} matcher found {len(matches)} matches")

            # Convert matches to Evidence objects
            evidence_list = []
            for match in matches:
                evidence = self._match_to_evidence(
                    match=match,
                    matcher=matcher,
                    org_id=org_id,
                    year=year,
                    doc_id=doc_id,
                    document_text=document_text
                )
                evidence_list.append(evidence)

            evidence_by_theme[theme] = evidence_list
            total_matches += len(matches)

        # Step 3: Create extraction result
        snapshot_id = self._generate_snapshot_id(org_id, year, doc_id)

        result = ExtractionResult(
            company_name=org_id,  # TODO: Resolve ticker -> company name
            year=year,
            doc_id=doc_id,
            evidence_by_theme=evidence_by_theme,
            extraction_timestamp=datetime.utcnow().isoformat(),
            snapshot_id=snapshot_id,
            metadata={
                "filing_url": filing_url,
                "document_length_chars": len(document_text),
                "total_pages": len(page_offsets),
                "total_matches": total_matches,
                "matchers_used": [m.theme for m in self.matchers]
            }
        )

        logger.info(
            f"Extraction complete: {result.get_total_evidence_count()} evidence items "
            f"across {result.get_theme_count()} themes"
        )

        return result

    def _match_to_evidence(
        self,
        match: Match,
        matcher: BaseMatcher,
        org_id: str,
        year: int,
        doc_id: str,
        document_text: str
    ) -> Evidence:
        """
        Convert a Match to an Evidence object with full metadata.

        Args:
            match: Match object from matcher
            matcher: The matcher that produced this match
            org_id: Organization identifier
            year: Fiscal year
            doc_id: Document identifier
            document_text: Full document text (for context extraction)

        Returns:
            Evidence object ready for storage
        """
        # Extract 30-word context using HTML parser
        context_30w = self.html_parser.extract_30_word_context(
            match.span_start,
            match.span_end
        )

        # Classify evidence type and get stage indicator
        evidence_type = matcher.classify_evidence_type(match)
        stage_indicator = matcher.get_stage_indicator(evidence_type)

        # Generate hash for deduplication
        hash_input = f"{org_id}:{year}:{match.span_start}:{match.span_end}:{match.match_text}"
        hash_sha256 = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        # Calculate confidence (simple heuristic for now)
        # TODO: Implement sophisticated confidence scoring
        confidence = 0.8  # Base confidence for pattern matches

        # Create Evidence object
        # Note: Evidence model doesn't have metadata field - pattern info is in evidence_type
        evidence = Evidence(
            evidence_id=Evidence.generate_evidence_id(),
            org_id=org_id,
            year=year,
            theme=matcher.theme,
            stage_indicator=stage_indicator,
            doc_id=doc_id,
            page_no=match.page_no,
            span_start=match.span_start,
            span_end=match.span_end,
            extract_30w=context_30w,
            hash_sha256=hash_sha256,
            confidence=confidence,
            evidence_type=evidence_type,
            snapshot_id=""  # Will be set by extraction result
        )

        return evidence

    def _generate_snapshot_id(self, org_id: str, year: int, doc_id: str) -> str:
        """
        Generate unique snapshot ID for this extraction run.

        Format: <org_id>_<year>_<timestamp_hash>
        """
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{org_id}:{year}:{doc_id}:{timestamp}"
        hash_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

        snapshot_id = f"{org_id}_{year}_{hash_suffix}"
        return snapshot_id

    def extract_from_file(
        self,
        html_file_path: Path,
        org_id: str,
        year: int,
        doc_id: str
    ) -> EvidenceExtractionResult:
        """
        Convenience method to extract evidence from HTML file.

        Args:
            html_file_path: Path to HTML file
            org_id: Organization identifier
            year: Fiscal year
            doc_id: Document identifier

        Returns:
            ExtractionResult with extracted evidence
        """
        logger.info(f"Reading HTML from {html_file_path}")
        html_content = html_file_path.read_text(encoding='utf-8', errors='ignore')

        filing_url = f"file://{html_file_path.absolute()}"

        return self.extract_from_html(
            html_content=html_content,
            org_id=org_id,
            year=year,
            doc_id=doc_id,
            filing_url=filing_url
        )


class BatchExtractor:
    """
    Batch process multiple companies/filings.

    For Option 1: Process 5 test companies (Microsoft, Apple, Tesla, ExxonMobil, Target)
    """

    def __init__(self, matchers: Optional[List[BaseMatcher]] = None):
        """Initialize batch extractor with given matchers."""
        self.extractor = EvidenceExtractor(matchers=matchers)

    def extract_batch(
        self,
        filings: List[Dict[str, str]]
    ) -> List[EvidenceExtractionResult]:
        """
        Extract evidence from multiple filings.

        Args:
            filings: List of dicts with keys: html_content, org_id, year, doc_id, filing_url

        Returns:
            List of ExtractionResult objects
        """
        results = []

        for i, filing in enumerate(filings, 1):
            logger.info(f"Processing filing {i}/{len(filings)}: {filing['org_id']} ({filing['year']})")

            try:
                result = self.extractor.extract_from_html(
                    html_content=filing['html_content'],
                    org_id=filing['org_id'],
                    year=filing['year'],
                    doc_id=filing['doc_id'],
                    filing_url=filing.get('filing_url', '')
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to extract from {filing['org_id']} ({filing['year']}): {e}")
                continue

        logger.info(f"Batch extraction complete: {len(results)}/{len(filings)} successful")
        return results
