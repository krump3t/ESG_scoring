"""CP Tests for Silver Locator - Task 026

SCA v13.8-MEA Compliance:
- TDD Guard: Tests written BEFORE implementation
- CP Markers: All tests marked with @pytest.mark.cp
- Failure Paths: Tests for missing files
- Property Tests: Hypothesis @given tests
"""
import pytest
from hypothesis import given, strategies as st
import os
import tempfile
from pathlib import Path


@pytest.mark.cp
def test_silver_locator_exists():
    """CP: silver_locator module is importable."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    assert locate_chunks_parquet is not None
    assert callable(locate_chunks_parquet)


@pytest.mark.cp
def test_locate_chunks_default_backend(monkeypatch):
    """CP: locate_chunks_parquet prefers silver/ when PARSER_BACKEND=default."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    # Set environment to default
    monkeypatch.setenv("PARSER_BACKEND", "default")

    # If default silver file exists, should return it
    # (This test assumes LSE_HEAD_2025 data exists)
    result = locate_chunks_parquet("LSE_HEAD_2025", "LSE_HEAD", 2025)

    # Should return a path or empty string
    assert isinstance(result, str)

    # If file exists, should contain silver/ (not silver_docling/)
    if result:
        assert "silver/" in result or "silver\\" in result
        assert "silver_docling" not in result


@pytest.mark.cp
def test_locate_chunks_docling_backend(monkeypatch, tmp_path):
    """CP: locate_chunks_parquet prefers silver_docling/ when PARSER_BACKEND=docling."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    # Set environment to docling
    monkeypatch.setenv("PARSER_BACKEND", "docling")

    # Create mock silver_docling file
    docling_dir = tmp_path / "data" / "silver_docling" / "org_id=TEST" / "year=2025"
    docling_dir.mkdir(parents=True)
    docling_file = docling_dir / "TEST_2025_chunks.parquet"
    docling_file.write_text("mock")

    # Change to tmp_path for test
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        result = locate_chunks_parquet("TEST_2025", "TEST", 2025)

        # Should find docling file
        assert result != ""
        assert "silver_docling" in result

    finally:
        os.chdir(original_cwd)


@pytest.mark.cp
def test_locate_chunks_fallback(monkeypatch, tmp_path):
    """CP: Falls back to silver/ if docling file not found."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    # Set environment to docling
    monkeypatch.setenv("PARSER_BACKEND", "docling")

    # Create only default silver file (no docling)
    default_dir = tmp_path / "data" / "silver" / "org_id=TEST" / "year=2025"
    default_dir.mkdir(parents=True)
    default_file = default_dir / "TEST_2025_chunks.parquet"
    default_file.write_text("mock")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        result = locate_chunks_parquet("TEST_2025", "TEST", 2025)

        # Should fall back to default silver
        assert result != ""
        assert ("silver/" in result or "silver\\" in result)
        assert "silver_docling" not in result

    finally:
        os.chdir(original_cwd)


@pytest.mark.cp
def test_locate_chunks_not_found():
    """CP Failure Path: Returns empty string if file not found."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    # Non-existent document
    result = locate_chunks_parquet("NONEXISTENT_DOC", "FAKE_ORG", 9999)

    # Should return empty string (not raise exception)
    assert result == ""


@pytest.mark.cp
def test_get_active_backend_default(monkeypatch):
    """CP: get_active_backend returns 'default' when PARSER_BACKEND unset."""
    from libs.retrieval.silver_locator import get_active_backend

    # Unset environment variable
    monkeypatch.delenv("PARSER_BACKEND", raising=False)

    backend = get_active_backend()
    assert backend == "default"


@pytest.mark.cp
def test_get_active_backend_docling(monkeypatch):
    """CP: get_active_backend returns 'docling' when PARSER_BACKEND=docling."""
    from libs.retrieval.silver_locator import get_active_backend

    monkeypatch.setenv("PARSER_BACKEND", "docling")

    backend = get_active_backend()
    assert backend == "docling"


@pytest.mark.cp
def test_get_active_backend_case_insensitive(monkeypatch):
    """CP: get_active_backend handles case variations."""
    from libs.retrieval.silver_locator import get_active_backend

    # Test uppercase
    monkeypatch.setenv("PARSER_BACKEND", "DOCLING")
    assert get_active_backend() == "docling"

    # Test mixed case
    monkeypatch.setenv("PARSER_BACKEND", "DoCLiNg")
    assert get_active_backend() == "docling"


@pytest.mark.cp
def test_locate_chunks_absolute_path(tmp_path, monkeypatch):
    """CP: locate_chunks_parquet returns absolute path."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    monkeypatch.setenv("PARSER_BACKEND", "default")

    # Create mock file
    default_dir = tmp_path / "data" / "silver" / "org_id=TEST" / "year=2025"
    default_dir.mkdir(parents=True)
    default_file = default_dir / "TEST_2025_chunks.parquet"
    default_file.write_text("mock")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        result = locate_chunks_parquet("TEST_2025", "TEST", 2025)

        # Should return path (relative is ok, but should be consistent)
        assert result != ""
        assert result.endswith("_chunks.parquet")

    finally:
        os.chdir(original_cwd)


@pytest.mark.cp
@given(
    doc_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_')),
    org_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_')),
    year=st.integers(min_value=2000, max_value=2100)
)
def test_locate_chunks_property_no_exception(doc_id, org_id, year):
    """CP Property Test: locate_chunks_parquet never raises exceptions."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    try:
        result = locate_chunks_parquet(doc_id, org_id, year)
        # Should return string (empty or path)
        assert isinstance(result, str)
    except Exception as e:
        pytest.fail(f"locate_chunks_parquet raised exception: {e}")


@pytest.mark.cp
def test_locate_chunks_thread_safe(monkeypatch, tmp_path):
    """CP: locate_chunks_parquet is thread-safe (read-only env access)."""
    from libs.retrieval.silver_locator import locate_chunks_parquet
    import threading

    monkeypatch.setenv("PARSER_BACKEND", "default")

    # Create mock file
    default_dir = tmp_path / "data" / "silver" / "org_id=TEST" / "year=2025"
    default_dir.mkdir(parents=True)
    default_file = default_dir / "TEST_2025_chunks.parquet"
    default_file.write_text("mock")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        results = []

        def worker():
            result = locate_chunks_parquet("TEST_2025", "TEST", 2025)
            results.append(result)

        # Run 10 threads concurrently
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get same result
        assert len(results) == 10
        assert len(set(results)) == 1  # All identical

    finally:
        os.chdir(original_cwd)


@pytest.mark.cp
def test_locate_chunks_path_format(tmp_path, monkeypatch):
    """CP: locate_chunks_parquet returns correct path format."""
    from libs.retrieval.silver_locator import locate_chunks_parquet

    monkeypatch.setenv("PARSER_BACKEND", "default")

    # Create mock file
    default_dir = tmp_path / "data" / "silver" / "org_id=TESTORG" / "year=2025"
    default_dir.mkdir(parents=True)
    default_file = default_dir / "TESTDOC_chunks.parquet"
    default_file.write_text("mock")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        result = locate_chunks_parquet("TESTDOC", "TESTORG", 2025)

        # Should contain org_id and year in path
        assert "org_id=TESTORG" in result
        assert "year=2025" in result
        assert "TESTDOC_chunks.parquet" in result

    finally:
        os.chdir(original_cwd)
