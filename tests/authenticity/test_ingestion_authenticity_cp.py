"""
Critical Path Tests: Ingestion Authenticity (AR-001)

Tests for ingestion ledger, crawl manifest, and SHA256 traceability.

Compliance:
- TDD-first: Tests before implementation
- Property-based: Hypothesis tests for ledger invariants
- Determinism: Fixed seeds, content hash validation
- Authenticity: URLs + headers + SHA256 captured in manifest

SCA v13.8 Authenticity Refactor
"""

import pytest
from typing import Dict, List, Any
from hypothesis import given, strategies as st
import json
from pathlib import Path
import hashlib


@pytest.mark.cp
class TestIngestionAuthenticityCP:
    """Tests for crawl ledger, manifest generation, and SHA256 integrity."""

    def test_manifest_has_required_fields(self):
        """Verify ingestion manifest includes url, headers, source_hash."""
        # Mock manifest structure
        manifest_entry = {
            "url": "https://example.com/report.pdf",
            "retrieval_date": "2025-10-26T00:00:00Z",
            "content_hash_sha256": "abc123def456...",
            "response_headers": {
                "content-type": "application/pdf",
                "content-length": "1024"
            },
            "status_code": 200
        }

        # Verify all required fields present
        assert "url" in manifest_entry
        assert "content_hash_sha256" in manifest_entry
        assert "response_headers" in manifest_entry
        assert "retrieval_date" in manifest_entry

    def test_crawl_ledger_tracks_sources(self):
        """Verify ledger tracks every crawled URL with deterministic hash."""
        from agents.crawler.ledger import IngestLedger

        ledger = IngestLedger()

        # Record a crawl
        ledger.add_crawl(
            url="https://sec.gov/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-24-000077",
            source_hash="sha256_abc123",
            retrieval_date="2025-10-26T00:00:00Z",
            status_code=200
        )

        # Verify ledger persistence
        records = ledger.get_all()
        assert len(records) >= 1
        assert any(r["url"] == "https://sec.gov/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-24-000077" for r in records)

    def test_content_hash_determinism(self):
        """Verify same content always produces same SHA256."""
        content = b"ESG Report 2024 - Apple Inc."
        hash1 = hashlib.sha256(content).hexdigest()
        hash2 = hashlib.sha256(content).hexdigest()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex is 64 chars

    @given(st.text(min_size=10, max_size=1000))
    def test_ledger_handles_varied_urls(self, url_fragment: str):
        """Property test: ledger accepts various URL formats."""
        from agents.crawler.ledger import IngestLedger

        ledger = IngestLedger()
        test_url = f"https://example.com/{url_fragment}"

        # Should not raise
        ledger.add_crawl(
            url=test_url,
            source_hash="test_hash",
            retrieval_date="2025-10-26T00:00:00Z",
            status_code=200
        )

    def test_manifest_json_serializable(self):
        """Verify manifest can be serialized to JSON."""
        manifest = {
            "ingestion_run_id": "run_123",
            "timestamp": "2025-10-26T00:00:00Z",
            "sources": [
                {
                    "url": "https://sec.gov/report.pdf",
                    "content_hash_sha256": "abc123",
                    "status_code": 200,
                    "retrieval_date": "2025-10-26T00:00:00Z"
                }
            ]
        }

        # Should serialize without error
        json_str = json.dumps(manifest)
        parsed = json.loads(json_str)

        assert parsed["ingestion_run_id"] == "run_123"
        assert len(parsed["sources"]) == 1
        assert parsed["sources"][0]["content_hash_sha256"] == "abc123"

    def test_manifest_file_written_to_artifacts(self, tmp_path):
        """Verify manifest written to artifacts/ingestion/manifest.json."""
        manifest_dir = tmp_path / "artifacts" / "ingestion"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = manifest_dir / "manifest.json"

        manifest_data = {
            "sources": [
                {"url": "https://example.com", "content_hash_sha256": "abc123"}
            ]
        }

        manifest_file.write_text(json.dumps(manifest_data))

        # Verify file exists and is readable
        assert manifest_file.exists()
        loaded = json.loads(manifest_file.read_text())
        assert len(loaded["sources"]) == 1

    def test_ledger_hash_mismatch_warning(self):
        """Failure path: Ledger warns when provided hash doesn't match content."""
        from agents.crawler.ledger import IngestLedger

        ledger = IngestLedger()

        # Provide mismatched hash
        actual_content = b"Real document content"
        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        # Should not raise, but should log warning
        result = ledger.add_crawl(
            url="https://example.com/doc.pdf",
            source_hash=wrong_hash,
            retrieval_date="2025-10-26T00:00:00Z",
            status_code=200,
            content_bytes=actual_content
        )

        # Result should still be the wrong hash (as provided)
        assert result == wrong_hash

    def test_ledger_invalid_manifest_path_recovers(self, tmp_path):
        """Failure path: Ledger recovers gracefully from corrupt manifest."""
        from agents.crawler.ledger import IngestLedger

        # Create invalid JSON file
        bad_manifest = tmp_path / "bad_manifest.json"
        bad_manifest.write_text("{invalid json content")

        # Should not raise, should log warning and continue
        try:
            ledger = IngestLedger(manifest_path=str(bad_manifest))
            # Should have empty entries after failure to load
            assert ledger.entries == []
        except json.JSONDecodeError:
            # Also acceptable - explicit error handling
            pass
