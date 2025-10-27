"""
Data validation pipeline for ESG report chunks
Validates schemas, enforces quality checks, handles deduplication, tracks lineage
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Set, Tuple
import os
import hashlib
import os
import logging
from datetime import datetime
from pathlib import Path
import os
import json
import os
import re
from libs.utils.clock import get_clock
clock = get_clock()


def get_audit_timestamp() -> str:
    """Get timestamp with AUDIT_TIME override support for determinism"""
    audit_time = os.getenv("AUDIT_TIME")
    if audit_time:
        return audit_time
    return get_audit_timestamp()

try:
    import pyarrow as pa
    import pyarrow.compute as pc
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    pa = None
    pc = None

import os
import numpy as np
from collections import defaultdict

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation checks"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class LineageRecord:
    """Data lineage tracking for chunks"""
    chunk_id: str
    source_pdf: str
    source_url: str
    company: str
    year: int
    crawl_timestamp: str
    parse_timestamp: str
    validation_timestamp: str
    parent_chunk_id: Optional[str] = None  # For split chunks
    transformation: Optional[str] = None  # What processing was done
    quality_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class ChunkValidator:
    """
    Validates chunk data quality and schema compliance
    """

    def __init__(
        self,
        min_text_length: int = 50,
        max_text_length: int = 10000,
        min_token_count: int = 10,
        max_token_count: int = 2000,
        similarity_threshold: float = 0.95,  # For deduplication
        cache_dir: Optional[Path] = None
    ):
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.min_token_count = min_token_count
        self.max_token_count = max_token_count
        self.similarity_threshold = similarity_threshold
        self.cache_dir = cache_dir or Path("data/validation_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Track seen chunks for deduplication
        self.chunk_hashes: Set[str] = set()
        self.chunk_embeddings: Dict[str, np.ndarray] = {}

        # Define PyArrow schema for chunks
        if PYARROW_AVAILABLE:
            self.chunk_schema = pa.schema([
                pa.field("chunk_id", pa.string(), nullable=False),
                pa.field("company", pa.string(), nullable=False),
                pa.field("year", pa.int32(), nullable=False),
                pa.field("text", pa.string(), nullable=False),
                pa.field("page_start", pa.int32(), nullable=False),
                pa.field("page_end", pa.int32(), nullable=False),
                pa.field("section", pa.string(), nullable=False),
                pa.field("source_url", pa.string(), nullable=False),
                pa.field("md5", pa.string(), nullable=False),
                pa.field("char_count", pa.int32(), nullable=True),
                pa.field("token_count_estimate", pa.int32(), nullable=True),
                pa.field("metadata", pa.string(), nullable=True)  # JSON string
            ])
        else:
            self.chunk_schema = None

        # Quality check patterns
        self.gibberish_pattern = re.compile(r'[^\x00-\x7F]{5,}')  # Non-ASCII sequences
        self.repetition_pattern = re.compile(r'(.)\1{10,}')  # Same char 10+ times
        self.url_pattern = re.compile(r'https?://[^\s]+')
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def validate_schema(self, chunk: Dict[str, Any]) -> ValidationResult:
        """Validate chunk against PyArrow schema"""
        errors = []
        warnings = []

        # Check required fields
        required_fields = [
            "chunk_id", "company", "year", "text",
            "page_start", "page_end", "section", "source_url", "md5"
        ]

        for field in required_fields:
            if field not in chunk:
                errors.append(f"Missing required field: {field}")

        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Validate with PyArrow if available
        if PYARROW_AVAILABLE and self.chunk_schema:
            try:
                # Convert metadata to JSON string if present
                chunk_copy = chunk.copy()
                if "metadata" in chunk_copy and chunk_copy["metadata"]:
                    chunk_copy["metadata"] = json.dumps(chunk_copy["metadata"])

                # Create table with single row
                table = pa.Table.from_pydict({
                    k: [v] for k, v in chunk_copy.items()
                    if k in [f.name for f in self.chunk_schema]
                })

                # Cast to schema (will raise if incompatible)
                table = table.cast(self.chunk_schema)

            except Exception as e:
                errors.append(f"Schema validation failed: {str(e)}")
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Type checks
        if not isinstance(chunk.get("year"), int):
            errors.append(f"Year must be integer, got {type(chunk.get('year'))}")

        if not isinstance(chunk.get("page_start"), int) or chunk["page_start"] < 1:
            errors.append("page_start must be positive integer")

        if not isinstance(chunk.get("page_end"), int) or chunk["page_end"] < chunk.get("page_start", 1):
            errors.append("page_end must be >= page_start")

        # MD5 format check
        if not re.match(r'^[a-f0-9]{32}$', chunk.get("md5", "")):
            errors.append("Invalid MD5 hash format")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_quality(self, chunk: Dict[str, Any]) -> ValidationResult:
        """Validate chunk data quality"""
        errors = []
        warnings = []
        metadata = {}

        text = chunk.get("text", "")

        # Text length checks
        if len(text) < self.min_text_length:
            errors.append(f"Text too short: {len(text)} < {self.min_text_length}")
        elif len(text) > self.max_text_length:
            warnings.append(f"Text unusually long: {len(text)} > {self.max_text_length}")

        # Token count checks
        token_count = chunk.get("token_count_estimate", len(text) // 4)
        if token_count < self.min_token_count:
            errors.append(f"Token count too low: {token_count} < {self.min_token_count}")
        elif token_count > self.max_token_count:
            warnings.append(f"Token count high: {token_count} > {self.max_token_count}")

        # Content quality checks

        # Check for gibberish
        gibberish_matches = self.gibberish_pattern.findall(text)
        if len(gibberish_matches) > 5:
            warnings.append(f"Possible encoding issues: {len(gibberish_matches)} non-ASCII sequences")

        # Check for repetition
        repetition_matches = self.repetition_pattern.findall(text)
        if repetition_matches:
            warnings.append(f"Excessive repetition detected: {repetition_matches[:3]}")

        # Check text diversity (unique words ratio)
        words = text.lower().split()
        if words:
            unique_ratio = len(set(words)) / len(words)
            metadata["unique_word_ratio"] = unique_ratio
            if unique_ratio < 0.3:
                warnings.append(f"Low text diversity: {unique_ratio:.2f}")

        # Check for sensitive data
        urls = self.url_pattern.findall(text)
        emails = self.email_pattern.findall(text)
        if urls:
            warnings.append(f"Contains {len(urls)} URLs")
            metadata["url_count"] = len(urls)
        if emails:
            warnings.append(f"Contains {len(emails)} email addresses")
            metadata["email_count"] = len(emails)

        # Calculate quality score
        quality_score = 1.0
        quality_score -= len(errors) * 0.2
        quality_score -= len(warnings) * 0.05
        quality_score = max(0.0, min(1.0, quality_score))
        metadata["quality_score"] = quality_score

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )

    def check_duplicate(self, chunk: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if chunk is duplicate based on MD5 and content similarity
        Returns: (is_duplicate, duplicate_chunk_id)
        """
        chunk_md5 = chunk.get("md5", "")
        chunk_id = chunk.get("chunk_id", "")

        # Check exact hash match
        if chunk_md5 in self.chunk_hashes:
            logger.info(f"Exact duplicate found for chunk {chunk_id}")
            return True, chunk_md5

        # Check similarity if embeddings available
        if hasattr(chunk, "embedding") and chunk.get("embedding") is not None:
            embedding = np.array(chunk["embedding"])

            # Compare with existing embeddings
            for existing_id, existing_emb in self.chunk_embeddings.items():
                similarity = np.dot(embedding, existing_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(existing_emb)
                )
                if similarity > self.similarity_threshold:
                    logger.info(f"Similar chunk found: {chunk_id} ~ {existing_id} (sim={similarity:.3f})")
                    return True, existing_id

            # Store for future comparisons
            self.chunk_embeddings[chunk_id] = embedding

        # Mark as seen
        self.chunk_hashes.add(chunk_md5)
        return False, None

    def create_lineage(
        self,
        chunk: Dict[str, Any],
        source_pdf: str,
        crawl_timestamp: str,
        parse_timestamp: str,
        parent_chunk_id: Optional[str] = None,
        transformation: Optional[str] = None
    ) -> LineageRecord:
        """Create lineage record for a chunk"""

        validation_result = self.validate_quality(chunk)
        quality_score = validation_result.metadata.get("quality_score", 0.0) if validation_result.metadata else 0.0

        return LineageRecord(
            chunk_id=chunk["chunk_id"],
            source_pdf=source_pdf,
            source_url=chunk["source_url"],
            company=chunk["company"],
            year=chunk["year"],
            crawl_timestamp=crawl_timestamp,
            parse_timestamp=parse_timestamp,
            validation_timestamp=get_audit_timestamp(),
            parent_chunk_id=parent_chunk_id,
            transformation=transformation,
            quality_score=quality_score
        )

    def validate_batch(
        self,
        chunks: List[Dict[str, Any]],
        source_pdf: str,
        crawl_timestamp: str,
        parse_timestamp: str,
        deduplicate: bool = True,
        track_lineage: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[ValidationResult], List[LineageRecord]]:
        """
        Validate a batch of chunks
        Returns: (valid_chunks, validation_results, lineage_records)
        """
        valid_chunks = []
        validation_results = []
        lineage_records = []

        # Group by company-year for context
        by_company_year = defaultdict(list)
        for chunk in chunks:
            key = (chunk.get("company", "unknown"), chunk.get("year", 0))
            by_company_year[key].append(chunk)

        logger.info(f"Validating {len(chunks)} chunks from {len(by_company_year)} company-year combinations")

        for chunk in chunks:
            # Schema validation
            schema_result = self.validate_schema(chunk)
            if not schema_result.is_valid:
                validation_results.append(schema_result)
                logger.warning(f"Schema validation failed for {chunk.get('chunk_id')}: {schema_result.errors}")
                continue

            # Quality validation
            quality_result = self.validate_quality(chunk)
            validation_results.append(quality_result)

            if not quality_result.is_valid:
                logger.warning(f"Quality validation failed for {chunk.get('chunk_id')}: {quality_result.errors}")
                continue

            # Deduplication check
            if deduplicate:
                is_duplicate, duplicate_id = self.check_duplicate(chunk)
                if is_duplicate:
                    logger.info(f"Skipping duplicate chunk {chunk.get('chunk_id')} (matches {duplicate_id})")
                    continue

            # Track lineage
            if track_lineage:
                lineage = self.create_lineage(
                    chunk=chunk,
                    source_pdf=source_pdf,
                    crawl_timestamp=crawl_timestamp,
                    parse_timestamp=parse_timestamp
                )
                lineage_records.append(lineage)

            valid_chunks.append(chunk)

        logger.info(f"Validation complete: {len(valid_chunks)}/{len(chunks)} chunks valid")

        # Save validation cache
        self._save_validation_state()

        return valid_chunks, validation_results, lineage_records

    def _save_validation_state(self):
        """Save validation state to cache"""
        state_file = self.cache_dir / "validation_state.json"

        try:
            state = {
                "chunk_hashes": list(self.chunk_hashes),
                "timestamp": get_audit_timestamp(),
                "stats": {
                    "total_chunks_seen": len(self.chunk_hashes),
                    "unique_embeddings": len(self.chunk_embeddings)
                }
            }

            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save validation state: {e}")

    def load_validation_state(self):
        """Load previous validation state from cache"""
        state_file = self.cache_dir / "validation_state.json"

        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)

                self.chunk_hashes = set(state.get("chunk_hashes", []))
                logger.info(f"Loaded {len(self.chunk_hashes)} known chunk hashes")

            except Exception as e:
                logger.warning(f"Failed to load validation state: {e}")


class DataLineageTracker:
    """
    Tracks data lineage and provenance through the pipeline
    """

    def __init__(self, lineage_dir: Optional[Path] = None):
        self.lineage_dir = lineage_dir or Path("data/lineage")
        self.lineage_dir.mkdir(parents=True, exist_ok=True)

        # Current session
        self.session_id = clock.now().strftime("%Y%m%d_%H%M%S")
        self.lineage_records: List[LineageRecord] = []

    def add_record(self, record: LineageRecord):
        """Add a lineage record"""
        self.lineage_records.append(record)

    def add_batch(self, records: List[LineageRecord]):
        """Add multiple lineage records"""
        self.lineage_records.extend(records)

    def save_lineage(self, filename: Optional[str] = None):
        """Save lineage records to file"""
        if not filename:
            filename = f"lineage_{self.session_id}.jsonl"

        lineage_file = self.lineage_dir / filename

        try:
            with open(lineage_file, 'w') as f:
                for record in self.lineage_records:
                    f.write(json.dumps(record.to_dict()) + '\n')

            logger.info(f"Saved {len(self.lineage_records)} lineage records to {lineage_file}")

        except Exception as e:
            logger.error(f"Failed to save lineage: {e}")

    def generate_lineage_report(self) -> Dict[str, Any]:
        """Generate summary report of data lineage"""

        if not self.lineage_records:
            return {"error": "No lineage records available"}

        # Aggregate statistics
        by_company = defaultdict(list)
        by_source = defaultdict(list)
        quality_scores = []

        for record in self.lineage_records:
            by_company[record.company].append(record)
            by_source[record.source_pdf].append(record)
            if record.quality_score:
                quality_scores.append(record.quality_score)

        report = {
            "session_id": self.session_id,
            "total_chunks": len(self.lineage_records),
            "companies": len(by_company),
            "sources": len(by_source),
            "average_quality": np.mean(quality_scores) if quality_scores else 0.0,
            "quality_distribution": {
                "min": min(quality_scores) if quality_scores else 0.0,
                "max": max(quality_scores) if quality_scores else 0.0,
                "median": np.median(quality_scores) if quality_scores else 0.0,
                "std": np.std(quality_scores) if quality_scores else 0.0
            },
            "by_company": {
                company: {
                    "chunks": len(records),
                    "years": list(set(r.year for r in records)),
                    "avg_quality": np.mean([r.quality_score for r in records if r.quality_score])
                }
                for company, records in by_company.items()
            },
            "timestamp": get_audit_timestamp()
        }

        return report


def validate_chunks(
    chunks: List[Dict[str, Any]],
    source_pdf: str = "unknown",
    crawl_timestamp: Optional[str] = None,
    parse_timestamp: Optional[str] = None,
    deduplicate: bool = True,
    track_lineage: bool = True,
    save_results: bool = True
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Main entry point for chunk validation
    Returns: (valid_chunks, validation_report)
    """

    if not crawl_timestamp:
        crawl_timestamp = get_audit_timestamp()
    if not parse_timestamp:
        parse_timestamp = get_audit_timestamp()

    # Initialize validator and tracker
    validator = ChunkValidator()
    validator.load_validation_state()

    tracker = DataLineageTracker()

    # Validate chunks
    valid_chunks, validation_results, lineage_records = validator.validate_batch(
        chunks=chunks,
        source_pdf=source_pdf,
        crawl_timestamp=crawl_timestamp,
        parse_timestamp=parse_timestamp,
        deduplicate=deduplicate,
        track_lineage=track_lineage
    )

    # Track lineage
    if track_lineage:
        tracker.add_batch(lineage_records)
        if save_results:
            tracker.save_lineage()

    # Generate report
    report = tracker.generate_lineage_report()
    report["validation_summary"] = {
        "total_input": len(chunks),
        "valid": len(valid_chunks),
        "invalid": len(chunks) - len(valid_chunks),
        "validation_errors": sum(1 for r in validation_results if not r.is_valid),
        "validation_warnings": sum(len(r.warnings) for r in validation_results)
    }

    return valid_chunks, report


if __name__ == "__main__":
    # Test the validator
    import sys

    logging.basicConfig(level=logging.INFO)

    # Create test chunks
    test_chunks = [
        {
            "chunk_id": "test_001",
            "company": "TestCorp",
            "year": 2023,
            "text": "This is a test chunk with sufficient content to pass validation checks. " * 5,
            "page_start": 1,
            "page_end": 1,
            "section": "Test Section",
            "source_url": "https://example.com/test.pdf",
            "md5": hashlib.md5("test content".encode()).hexdigest(),
            "char_count": 200,
            "token_count_estimate": 50
        },
        {
            "chunk_id": "test_002",
            "company": "TestCorp",
            "year": 2023,
            "text": "Short",  # Will fail minimum length
            "page_start": 2,
            "page_end": 2,
            "section": "Test Section",
            "source_url": "https://example.com/test.pdf",
            "md5": hashlib.md5("short".encode()).hexdigest(),
            "char_count": 5,
            "token_count_estimate": 1
        }
    ]

    # Validate
    valid, report = validate_chunks(test_chunks, source_pdf="test.pdf")

    print(f"\nValidation Results:")
    print(f"  Valid chunks: {len(valid)}/{len(test_chunks)}")
    print(f"\nValidation Report:")
    print(json.dumps(report, indent=2))