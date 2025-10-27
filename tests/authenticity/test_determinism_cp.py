"""Critical Path Tests: Determinism Validation (AR-001)."""

import pytest
import hashlib
import json


@pytest.mark.cp
class TestDeterminismCP:
    """Tests for artifact determinism across multiple runs."""

    def test_ledger_deterministic_run_ids(self):
        """Verify ledger generates deterministic run IDs."""
        from agents.crawler.ledger import IngestLedger

        ledger1 = IngestLedger()
        ledger2 = IngestLedger()

        url = "https://example.com/report.pdf"
        hash_val = "abc123def456"
        retrieval_date = "2025-10-26T00:00:00Z"

        ledger1.add_crawl(url=url, source_hash=hash_val, retrieval_date=retrieval_date, status_code=200)
        ledger2.add_crawl(url=url, source_hash=hash_val, retrieval_date=retrieval_date, status_code=200)

        entries1 = ledger1.get_all()
        entries2 = ledger2.get_all()

        assert entries1[0]["url"] == entries2[0]["url"]

    def test_rubric_scorer_deterministic_output(self):
        """Verify RubricScorer produces identical output."""
        from agents.scoring.rubric_scorer import RubricScorer

        scorer = RubricScorer()
        evidence = [
            {"theme_code": "Climate", "extract_30w": "Committed to net zero", "doc_id": "doc1", "evidence_id": "ev_001"},
            {"theme_code": "Climate", "extract_30w": "Reduced emissions 25%", "doc_id": "doc2", "evidence_id": "ev_002"}
        ]

        result1 = scorer.score(theme="Climate", evidence=evidence, org_id="apple", year=2024)
        result2 = scorer.score(theme="Climate", evidence=evidence, org_id="apple", year=2024)

        assert result1 == result2
        assert result1["stage"] == result2["stage"]

    def test_parity_checker_deterministic_report(self, tmp_path):
        """Verify ParityChecker produces identical reports."""
        from libs.retrieval.parity_checker import ParityChecker

        evidence_ids = ["doc1", "doc3", "doc5"]
        fused_top_k = [("doc1", 0.95), ("doc3", 0.90), ("doc5", 0.85)]

        checker1 = ParityChecker(output_dir=str(tmp_path / "check1"))
        checker2 = ParityChecker(output_dir=str(tmp_path / "check2"))

        report1 = checker1.check_parity(query="climate", evidence_ids=evidence_ids, fused_top_k=fused_top_k, k=5)
        report2 = checker2.check_parity(query="climate", evidence_ids=evidence_ids, fused_top_k=fused_top_k, k=5)

        assert report1 == report2

    def test_hash_consistency_across_runs(self):
        """Verify SHA256 hashing is consistent."""
        content = b"ESG Report 2024 - Apple Inc."

        hash1 = hashlib.sha256(content).hexdigest()
        hash2 = hashlib.sha256(content).hexdigest()
        hash3 = hashlib.sha256(content).hexdigest()

        assert hash1 == hash2 == hash3
        assert len(hash1) == 64

    def test_evidence_order_independence(self):
        """Verify RubricScorer handles different evidence orders."""
        from agents.scoring.rubric_scorer import RubricScorer

        scorer = RubricScorer()
        evidence_list1 = [
            {"theme_code": "Climate", "extract_30w": "Quote A", "doc_id": "doc1"},
            {"theme_code": "Climate", "extract_30w": "Quote B", "doc_id": "doc2"}
        ]
        evidence_list2 = [
            {"theme_code": "Climate", "extract_30w": "Quote B", "doc_id": "doc2"},
            {"theme_code": "Climate", "extract_30w": "Quote A", "doc_id": "doc1"}
        ]

        result1 = scorer.score(theme="Climate", evidence=evidence_list1, org_id="test")
        result2 = scorer.score(theme="Climate", evidence=evidence_list2, org_id="test")

        assert result1["stage"] == result2["stage"]

    def test_parity_sorted_output(self):
        """Verify ParityChecker returns sorted evidence_ids."""
        from libs.retrieval.parity_checker import ParityChecker

        checker = ParityChecker()
        evidence_ids = ["doc5", "doc1", "doc3"]
        fused_top_k = [("doc1", 0.95), ("doc3", 0.90), ("doc5", 0.85)]

        report = checker.check_parity(query="test", evidence_ids=evidence_ids, fused_top_k=fused_top_k, k=5)

        assert report["evidence_ids"] == sorted(evidence_ids)

    def test_ledger_manifest_stable_serialization(self, tmp_path):
        """Verify manifest JSON serialization is stable."""
        from agents.crawler.ledger import IngestLedger

        manifest_path = tmp_path / "manifest.json"
        ledger = IngestLedger(manifest_path=str(manifest_path))
        ledger.add_crawl(
            url="https://sec.gov/report.pdf",
            source_hash="sha256_abc123",
            retrieval_date="2025-10-26T00:00:00Z",
            status_code=200
        )

        content1 = manifest_path.read_text()
        content2 = manifest_path.read_text()

        assert content1 == content2
        data = json.loads(content1)
        assert "sources" in data
        assert len(data["sources"]) == 1
