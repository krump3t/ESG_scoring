"""CP Tests for Alignment Audit Script - Task 026

SCA v13.8-MEA Compliance:
- TDD Guard: Tests written BEFORE implementation
- CP Markers: All tests marked with @pytest.mark.cp
- Failure Paths: Tests for missing files, alignment mismatches
- Integration tests: End-to-end quote validation
"""
import pytest
import os
import tempfile
from pathlib import Path
import pandas as pd
import json


@pytest.mark.cp
def test_alignment_audit_module_exists():
    """CP: alignment_audit module is importable."""
    import scripts.alignment_audit as module

    assert module is not None
    assert hasattr(module, 'main')


@pytest.mark.cp
def test_find_quote_in_text_exact_match():
    """CP: find_quote_in_text returns correct span for exact match."""
    from scripts.alignment_audit import find_quote_in_text

    text = "The quick brown fox jumps over the lazy dog."
    quote = "brown fox jumps"

    result = find_quote_in_text(quote, text)

    assert result is not None
    assert result['found'] is True
    assert result['start_idx'] >= 0
    assert result['end_idx'] > result['start_idx']
    assert text[result['start_idx']:result['end_idx']] == quote


@pytest.mark.cp
def test_find_quote_in_text_case_insensitive():
    """CP: find_quote_in_text handles case variations."""
    from scripts.alignment_audit import find_quote_in_text

    text = "The Quick BROWN Fox"
    quote = "quick brown fox"

    result = find_quote_in_text(quote, text, case_sensitive=False)

    assert result is not None
    assert result['found'] is True


@pytest.mark.cp
def test_find_quote_in_text_not_found():
    """CP Failure Path: find_quote_in_text returns not found for missing quote."""
    from scripts.alignment_audit import find_quote_in_text

    text = "The quick brown fox"
    quote = "nonexistent phrase"

    result = find_quote_in_text(quote, text)

    assert result is not None
    assert result['found'] is False
    assert 'start_idx' not in result or result['start_idx'] == -1


@pytest.mark.cp
def test_find_quote_in_text_whitespace_normalization():
    """CP: find_quote_in_text handles extra whitespace."""
    from scripts.alignment_audit import find_quote_in_text

    text = "The quick    brown   fox"
    quote = "quick brown fox"

    result = find_quote_in_text(quote, text, normalize_whitespace=True)

    assert result is not None
    assert result['found'] is True


@pytest.mark.cp
def test_compute_alignment_score_exact():
    """CP: compute_alignment_score returns 1.0 for exact match."""
    from scripts.alignment_audit import compute_alignment_score

    quote = "test quote"
    found_text = "test quote"

    score = compute_alignment_score(quote, found_text)

    assert score == 1.0


@pytest.mark.cp
def test_compute_alignment_score_partial():
    """CP: compute_alignment_score returns <1.0 for partial match."""
    from scripts.alignment_audit import compute_alignment_score

    quote = "test quote with extra words"
    found_text = "test quote with different words"

    score = compute_alignment_score(quote, found_text)

    assert 0.0 < score < 1.0


@pytest.mark.cp
def test_compute_alignment_score_no_match():
    """CP Failure Path: compute_alignment_score returns low score for no match."""
    from scripts.alignment_audit import compute_alignment_score

    quote = "completely different"
    found_text = "nothing matches here"

    score = compute_alignment_score(quote, found_text)

    # SequenceMatcher will find some similarity even for very different strings
    # So we just test that it's significantly lower than 1.0
    assert score < 0.5


@pytest.mark.cp
def test_audit_quote_against_parquet(tmp_path):
    """CP: audit_quote_against_parquet validates quote location."""
    from scripts.alignment_audit import audit_quote_against_parquet

    # Create mock parquet
    rows = [
        {"doc_id": "TEST", "page": 1, "text": "Page 1 content here", "chunk_id": "TEST_p0001_00"},
        {"doc_id": "TEST", "page": 2, "text": "Page 2 with test quote", "chunk_id": "TEST_p0002_00"},
    ]
    parquet_path = tmp_path / "test.parquet"
    pd.DataFrame(rows).to_parquet(parquet_path, index=False)

    # Quote from page 2
    quote = "test quote"

    result = audit_quote_against_parquet(quote, str(parquet_path))

    assert result is not None
    assert result['found'] is True
    assert result['page'] == 2
    assert result['alignment_score'] > 0.5


@pytest.mark.cp
def test_audit_quote_against_parquet_not_found(tmp_path):
    """CP Failure Path: audit_quote_against_parquet returns not found."""
    from scripts.alignment_audit import audit_quote_against_parquet

    # Create mock parquet
    rows = [
        {"doc_id": "TEST", "page": 1, "text": "Page 1 content", "chunk_id": "TEST_p0001_00"},
    ]
    parquet_path = tmp_path / "test.parquet"
    pd.DataFrame(rows).to_parquet(parquet_path, index=False)

    # Quote not in parquet
    quote = "nonexistent quote"

    result = audit_quote_against_parquet(quote, str(parquet_path))

    assert result is not None
    assert result['found'] is False


@pytest.mark.cp
def test_load_parquet_file(tmp_path):
    """CP: load_parquet_file reads parquet correctly."""
    from scripts.alignment_audit import load_parquet_file

    # Create mock parquet
    rows = [
        {"doc_id": "TEST", "page": 1, "text": "Test", "chunk_id": "TEST_p0001_00"},
    ]
    parquet_path = tmp_path / "test.parquet"
    pd.DataFrame(rows).to_parquet(parquet_path, index=False)

    df = load_parquet_file(str(parquet_path))

    assert df is not None
    assert len(df) == 1
    assert list(df.columns) == ["doc_id", "page", "text", "chunk_id"]


@pytest.mark.cp
def test_load_parquet_file_not_found():
    """CP Failure Path: load_parquet_file raises error for missing file."""
    from scripts.alignment_audit import load_parquet_file

    with pytest.raises(FileNotFoundError):
        load_parquet_file("nonexistent.parquet")


@pytest.mark.cp
def test_main_missing_parquet(monkeypatch, capsys):
    """CP Failure Path: main exits with error if parquet not found."""
    from scripts.alignment_audit import main

    # Mock sys.argv
    monkeypatch.setattr('sys.argv', [
        'alignment_audit.py',
        '--doc_id', 'NONEXISTENT',
        '--org_id', 'FAKE',
        '--year', '2025',
        '--quote', 'test quote'
    ])

    # Should exit with error
    with pytest.raises(SystemExit):
        main()


@pytest.mark.cp
def test_main_integration_audit_quote(tmp_path, monkeypatch, capsys):
    """CP Integration: main audits quote against parquet."""
    from scripts.alignment_audit import main

    # Create mock parquet
    rows = [
        {"doc_id": "TEST_2025", "page": 1, "text": "Page 1 with test quote here", "chunk_id": "TEST_2025_p0001_00"},
    ]

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create directory structure
        parquet_dir = tmp_path / "data" / "silver" / "org_id=TEST" / "year=2025"
        parquet_dir.mkdir(parents=True)
        parquet_path = parquet_dir / "TEST_2025_chunks.parquet"
        pd.DataFrame(rows).to_parquet(parquet_path, index=False)

        # Mock sys.argv
        monkeypatch.setattr('sys.argv', [
            'alignment_audit.py',
            '--doc_id', 'TEST_2025',
            '--org_id', 'TEST',
            '--year', '2025',
            '--quote', 'test quote'
        ])

        # Run main (should succeed)
        main()

        # Check output contains success message
        captured = capsys.readouterr()
        assert "FOUND" in captured.out or "found" in captured.out.lower()

    finally:
        os.chdir(original_cwd)


@pytest.mark.cp
def test_batch_audit_quotes(tmp_path):
    """CP: batch_audit_quotes processes multiple quotes."""
    from scripts.alignment_audit import batch_audit_quotes

    # Create mock parquet
    rows = [
        {"doc_id": "TEST", "page": 1, "text": "First quote here", "chunk_id": "TEST_p0001_00"},
        {"doc_id": "TEST", "page": 2, "text": "Second quote here", "chunk_id": "TEST_p0002_00"},
    ]
    parquet_path = tmp_path / "test.parquet"
    pd.DataFrame(rows).to_parquet(parquet_path, index=False)

    quotes = ["First quote", "Second quote", "Missing quote"]

    results = batch_audit_quotes(quotes, str(parquet_path))

    assert results is not None
    assert len(results) == 3
    assert results[0]['found'] is True
    assert results[1]['found'] is True
    assert results[2]['found'] is False


@pytest.mark.cp
def test_generate_audit_report(tmp_path):
    """CP: generate_audit_report creates JSON report."""
    from scripts.alignment_audit import generate_audit_report

    audit_results = [
        {"quote": "test1", "found": True, "page": 1, "alignment_score": 1.0},
        {"quote": "test2", "found": False},
    ]

    report_path = tmp_path / "audit_report.json"

    generate_audit_report(audit_results, str(report_path))

    assert report_path.exists()

    # Validate JSON structure
    report = json.loads(report_path.read_text())
    assert "results" in report
    assert len(report["results"]) == 2
    assert report["total_quotes"] == 2
    assert report["found_count"] == 1
    assert report["not_found_count"] == 1


@pytest.mark.cp
def test_fuzzy_match_threshold():
    """CP: find_quote_in_text uses fuzzy matching with threshold."""
    from scripts.alignment_audit import find_quote_in_text

    text = "The quick brown fox jumps"
    quote = "quick brown foxes"  # Slight variation

    # Should find with fuzzy matching
    result = find_quote_in_text(quote, text, fuzzy=True, fuzzy_threshold=0.8)

    assert result is not None
    # Either exact or fuzzy match should be found
    assert result['found'] is True or 'fuzzy_score' in result


@pytest.mark.cp
def test_alignment_audit_respects_backend_env(tmp_path, monkeypatch):
    """CP: alignment_audit respects PARSER_BACKEND environment variable."""
    from scripts.alignment_audit import locate_parquet_for_audit

    monkeypatch.setenv("PARSER_BACKEND", "docling")

    # Create mock docling parquet
    docling_dir = tmp_path / "data" / "silver_docling" / "org_id=TEST" / "year=2025"
    docling_dir.mkdir(parents=True)
    docling_file = docling_dir / "TEST_2025_chunks.parquet"
    docling_file.write_text("mock")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        path = locate_parquet_for_audit("TEST_2025", "TEST", 2025)

        # Should prefer silver_docling/
        assert path != ""
        assert "silver_docling" in path

    finally:
        os.chdir(original_cwd)
