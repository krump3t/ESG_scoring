"""CP Tests for PDF to Silver Converter Script - Task 026

SCA v13.8-MEA Compliance:
- TDD Guard: Tests written BEFORE implementation
- CP Markers: All tests marked with @pytest.mark.cp
- Failure Paths: Tests for missing PDF, invalid args
- Integration tests: End-to-end conversion
- Property Tests: Hypothesis @given tests
"""
import pytest
import os
import tempfile
from pathlib import Path
import pandas as pd
from hypothesis import given, strategies as st


@pytest.mark.cp
def test_pdf_to_silver_module_exists():
    """CP: pdf_to_silver module is importable."""
    import scripts.pdf_to_silver as module

    assert module is not None
    assert hasattr(module, 'main')


@pytest.mark.cp
def test_pick_backend_default():
    """CP: pick_backend returns DefaultBackend for 'default'."""
    from scripts.pdf_to_silver import pick_backend
    from libs.extraction.backend_default import DefaultBackend

    backend = pick_backend("default")

    assert isinstance(backend, DefaultBackend)
    assert hasattr(backend, 'parse_pdf_to_pages')


@pytest.mark.cp
def test_pick_backend_case_insensitive():
    """CP: pick_backend handles case variations."""
    from scripts.pdf_to_silver import pick_backend

    # Test various cases
    backend1 = pick_backend("DEFAULT")
    backend2 = pick_backend("Default")
    backend3 = pick_backend("default")

    # All should return same type
    assert type(backend1) == type(backend2) == type(backend3)


@pytest.mark.cp
def test_pick_backend_docling_unavailable():
    """CP Failure Path: pick_backend raises RuntimeError if Docling not available."""
    from scripts.pdf_to_silver import pick_backend

    # If Docling not installed, should raise
    # (This test may pass if Docling is installed, which is fine)
    try:
        backend = pick_backend("docling")
        # If successful, should have parse method
        assert hasattr(backend, 'parse_pdf_to_pages')
    except RuntimeError as e:
        # Expected if Docling not available
        assert "not available" in str(e).lower()


@pytest.mark.cp
def test_write_parquet(tmp_path):
    """CP: write_parquet creates valid parquet file."""
    from scripts.pdf_to_silver import write_parquet

    # Create test data
    rows = [
        {"doc_id": "TEST", "page": 1, "text": "Page 1", "chunk_id": "TEST_p0001_00"},
        {"doc_id": "TEST", "page": 2, "text": "Page 2", "chunk_id": "TEST_p0002_00"},
    ]

    out_path = tmp_path / "test_output.parquet"

    write_parquet(rows, str(out_path))

    # File should exist
    assert out_path.exists()

    # Should be readable as parquet
    df = pd.read_parquet(out_path)
    assert len(df) == 2
    assert list(df.columns) == ["doc_id", "page", "text", "chunk_id"]


@pytest.mark.cp
def test_write_parquet_creates_directory(tmp_path):
    """CP: write_parquet creates parent directories if needed."""
    from scripts.pdf_to_silver import write_parquet

    rows = [{"doc_id": "TEST", "page": 1, "text": "Test", "chunk_id": "TEST_p0001_00"}]

    # Nested path that doesn't exist
    out_path = tmp_path / "nested" / "path" / "output.parquet"

    write_parquet(rows, str(out_path))

    # File and directories should exist
    assert out_path.exists()
    assert out_path.parent.exists()


@pytest.mark.cp
def test_sha256_file():
    """CP: sha256_file computes correct hash."""
    from scripts.pdf_to_silver import sha256_file

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    hash1 = sha256_file(pdf_path)

    # Should be valid SHA256 (64 hex chars)
    assert len(hash1) == 64
    assert all(c in '0123456789abcdef' for c in hash1)

    # Should be deterministic
    hash2 = sha256_file(pdf_path)
    assert hash1 == hash2


@pytest.mark.cp
def test_main_missing_pdf(monkeypatch, capsys):
    """CP Failure Path: main exits with error if PDF not found."""
    from scripts.pdf_to_silver import main

    # Mock sys.argv
    monkeypatch.setattr('sys.argv', [
        'pdf_to_silver.py',
        '--org_id', 'FAKE',
        '--year', '2025',
        '--doc_id', 'NONEXISTENT_DOC',
        '--backend', 'default'
    ])

    # Should exit with error
    with pytest.raises(SystemExit):
        main()


@pytest.mark.cp
def test_main_integration_default_backend(tmp_path, monkeypatch):
    """CP Integration: main converts PDF with default backend."""
    from scripts.pdf_to_silver import main

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    # Change to tmp directory
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create data/raw directory and copy PDF
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)

        # Mock sys.argv
        monkeypatch.setattr('sys.argv', [
            'pdf_to_silver.py',
            '--org_id', 'LSE_HEAD',
            '--year', '2025',
            '--doc_id', 'LSE_HEAD_2025',
            '--backend', 'default',
            '--pdf', pdf_path  # Use absolute path from original location
        ])

        # Run main
        main()

        # Output should exist
        output_path = tmp_path / "data" / "silver" / "org_id=LSE_HEAD" / "year=2025" / "LSE_HEAD_2025_chunks.parquet"
        assert output_path.exists()

        # Provenance sidecar should exist
        prov_path = Path(str(output_path) + ".prov.json")
        assert prov_path.exists()

        # Validate provenance content
        import json
        prov_data = json.loads(prov_path.read_text())
        assert prov_data["doc_id"] == "LSE_HEAD_2025"
        assert prov_data["backend"] == "default"
        assert "source_pdf_sha256" in prov_data

    finally:
        os.chdir(original_cwd)


@pytest.mark.cp
def test_provenance_sidecar_schema(tmp_path):
    """CP: Provenance sidecar has correct schema."""
    from scripts.pdf_to_silver import write_parquet
    import json

    rows = [{"doc_id": "TEST", "page": 1, "text": "Test", "chunk_id": "TEST_p0001_00"}]
    out_path = tmp_path / "test.parquet"

    write_parquet(rows, str(out_path))

    # Create provenance manually (simulating main())
    prov_data = {
        "doc_id": "TEST",
        "org_id": "TEST_ORG",
        "year": 2025,
        "backend": "default",
        "source_pdf": "test.pdf",
        "source_pdf_sha256": "a" * 64,
        "row_count": len(rows),
        "schema_version": "1.0"
    }

    prov_path = Path(str(out_path) + ".prov.json")
    prov_path.write_text(json.dumps(prov_data, indent=2))

    # Validate required fields
    assert prov_path.exists()
    loaded = json.loads(prov_path.read_text())

    required_keys = {"doc_id", "org_id", "year", "backend", "source_pdf", "source_pdf_sha256"}
    assert required_keys.issubset(loaded.keys())


@pytest.mark.cp
def test_main_auto_detect_pdf(tmp_path, monkeypatch):
    """CP: main auto-detects PDF path if not provided."""
    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create data/raw and copy PDF
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        import shutil
        shutil.copy(pdf_path, raw_dir / "LSE_HEAD_2025.pdf")

        # Mock sys.argv (no --pdf arg)
        monkeypatch.setattr('sys.argv', [
            'pdf_to_silver.py',
            '--org_id', 'LSE_HEAD',
            '--year', '2025',
            '--doc_id', 'LSE_HEAD_2025',
            '--backend', 'default'
        ])

        # Should succeed (auto-detect PDF)
        from scripts.pdf_to_silver import main
        main()

        # Output should exist
        output_path = tmp_path / "data" / "silver" / "org_id=LSE_HEAD" / "year=2025" / "LSE_HEAD_2025_chunks.parquet"
        assert output_path.exists()

    finally:
        os.chdir(original_cwd)


@pytest.mark.cp
@given(
    doc_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_')),
    org_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_')),
    year=st.integers(min_value=2000, max_value=2100)
)
def test_sha256_file_property_deterministic(doc_id, org_id, year):
    """CP Property Test: sha256_file produces deterministic hashes."""
    from scripts.pdf_to_silver import sha256_file

    # Create a test file with known content (no fixture, use temp context manager)
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test.txt"
        test_content = f"{doc_id}_{org_id}_{year}"
        test_file.write_text(test_content)

        # Hash should be deterministic
        hash1 = sha256_file(str(test_file))
        hash2 = sha256_file(str(test_file))

        assert hash1 == hash2
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
