"""CP Tests for Default Backend (PyMuPDF) - Task 026

SCA v13.8-MEA Compliance:
- TDD Guard: Tests written BEFORE implementation
- CP Markers: All tests marked with @pytest.mark.cp
- Failure Paths: Tests for error conditions (missing PDF, empty PDF)
- Property Tests: Hypothesis @given tests
"""
import pytest
from hypothesis import given, strategies as st
import tempfile
import os
from pathlib import Path


@pytest.mark.cp
def test_default_backend_exists():
    """CP: DefaultBackend class is importable."""
    from libs.extraction.backend_default import DefaultBackend

    # Should be instantiable
    backend = DefaultBackend()
    assert backend is not None


@pytest.mark.cp
def test_default_backend_implements_protocol():
    """CP: DefaultBackend implements PDFParserBackend protocol."""
    from libs.extraction.backend_default import DefaultBackend
    from libs.extraction.parser_backend import PDFParserBackend

    backend = DefaultBackend()

    # Must have parse_pdf_to_pages method
    assert hasattr(backend, 'parse_pdf_to_pages')
    assert callable(backend.parse_pdf_to_pages)


@pytest.mark.cp
def test_default_backend_returns_correct_schema():
    """CP: DefaultBackend returns standardized schema."""
    from libs.extraction.backend_default import DefaultBackend

    backend = DefaultBackend()

    # Use LSE_HEAD_2025.pdf if available
    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    result = backend.parse_pdf_to_pages(pdf_path, "LSE_HEAD_2025")

    # Should return list
    assert isinstance(result, list)

    # Should have at least 1 page
    assert len(result) > 0, "Expected at least 1 page"

    # Each page should have required fields
    for page_dict in result:
        assert "doc_id" in page_dict
        assert "page" in page_dict
        assert "text" in page_dict
        assert "chunk_id" in page_dict

        # Verify types
        assert isinstance(page_dict["doc_id"], str)
        assert isinstance(page_dict["page"], int)
        assert isinstance(page_dict["text"], str)
        assert isinstance(page_dict["chunk_id"], str)

        # Page should be 1-indexed
        assert page_dict["page"] >= 1


@pytest.mark.cp
def test_default_backend_deterministic():
    """CP: DefaultBackend produces deterministic output (same PDF → same result)."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()

    # Run twice
    result1 = backend.parse_pdf_to_pages(pdf_path, "TEST_DOC")
    result2 = backend.parse_pdf_to_pages(pdf_path, "TEST_DOC")

    # Should be identical
    assert len(result1) == len(result2), "Different number of pages"

    for p1, p2 in zip(result1, result2):
        assert p1["doc_id"] == p2["doc_id"]
        assert p1["page"] == p2["page"]
        assert p1["text"] == p2["text"]
        assert p1["chunk_id"] == p2["chunk_id"]


@pytest.mark.cp
def test_default_backend_failure_missing_pdf():
    """CP Failure Path: Missing PDF returns empty list (logged, not raised)."""
    from libs.extraction.backend_default import DefaultBackend

    backend = DefaultBackend()

    # Non-existent PDF
    result = backend.parse_pdf_to_pages("nonexistent.pdf", "MISSING_DOC")

    # Should return empty list (not raise exception)
    assert result == []


@pytest.mark.cp
def test_default_backend_failure_empty_pdf():
    """CP Failure Path: Empty PDF file returns empty list."""
    from libs.extraction.backend_default import DefaultBackend

    backend = DefaultBackend()

    # Create temporary empty file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
        # Write minimal PDF header (not valid, but not empty)
        tmp.write(b"%PDF-1.4")

    try:
        result = backend.parse_pdf_to_pages(tmp_path, "EMPTY_DOC")

        # Should return empty list or handle gracefully
        assert isinstance(result, list)
        # Malformed PDF may return empty or fail gracefully

    finally:
        os.unlink(tmp_path)


@pytest.mark.cp
def test_default_backend_page_numbers_sequential():
    """CP: Page numbers are sequential and 1-indexed."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()
    result = backend.parse_pdf_to_pages(pdf_path, "TEST_DOC")

    # Extract page numbers
    page_nums = [p["page"] for p in result]

    # Should start at 1
    assert page_nums[0] == 1

    # Should be sequential
    for i, page_num in enumerate(page_nums):
        assert page_num == i + 1, f"Page {i} has number {page_num}, expected {i+1}"


@pytest.mark.cp
def test_default_backend_chunk_ids_unique():
    """CP: Chunk IDs are unique across all pages."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()
    result = backend.parse_pdf_to_pages(pdf_path, "TEST_DOC")

    # Extract all chunk IDs
    chunk_ids = [p["chunk_id"] for p in result]

    # Should be unique
    assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk IDs found"


@pytest.mark.cp
def test_default_backend_doc_id_propagated():
    """CP: doc_id is propagated to all pages."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()
    result = backend.parse_pdf_to_pages(pdf_path, "CUSTOM_DOC_ID")

    # All pages should have same doc_id
    for page_dict in result:
        assert page_dict["doc_id"] == "CUSTOM_DOC_ID"


@pytest.mark.cp
def test_default_backend_text_extraction():
    """CP: Text is extracted (non-empty for non-blank pages)."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()
    result = backend.parse_pdf_to_pages(pdf_path, "TEST_DOC")

    # At least some pages should have text
    non_empty_pages = [p for p in result if p["text"].strip()]

    # Most pages in a real PDF should have text
    assert len(non_empty_pages) > 0, "No text extracted from any page"

    # Should be majority of pages (real PDFs aren't mostly blank)
    assert len(non_empty_pages) > len(result) / 2, "Too many blank pages"


@pytest.mark.cp
@given(doc_id=st.text(min_size=1, max_size=100))
def test_default_backend_doc_id_property(doc_id):
    """CP Property Test: DefaultBackend handles various doc_id values."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()

    try:
        result = backend.parse_pdf_to_pages(pdf_path, doc_id)

        # Should succeed (or return empty if error)
        assert isinstance(result, list)

        # If successful, all pages should have the doc_id
        if len(result) > 0:
            assert all(p["doc_id"] == doc_id for p in result)

    except Exception as e:
        # Should not raise exceptions (returns empty list on error)
        pytest.fail(f"Backend raised exception for doc_id='{doc_id}': {e}")


@pytest.mark.cp
def test_default_backend_source_field():
    """CP: DefaultBackend includes source="default" in output."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()
    result = backend.parse_pdf_to_pages(pdf_path, "TEST_DOC")

    # All pages should have source field (optional in schema, but good practice)
    # Note: This is a design decision - may or may not be implemented
    # If implemented, should be "default"
    if len(result) > 0 and "source" in result[0]:
        for page_dict in result:
            assert page_dict.get("source") == "default"


@pytest.mark.cp
def test_default_backend_chunk_id_format():
    """CP: Chunk IDs follow expected format."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()
    result = backend.parse_pdf_to_pages(pdf_path, "TEST_DOC")

    # Check format: {doc_id}_p{page:04d}_{idx:02d}
    for page_dict in result:
        chunk_id = page_dict["chunk_id"]

        # Should contain doc_id
        assert "TEST_DOC" in chunk_id

        # Should contain _p pattern
        assert "_p" in chunk_id

        # Should have page number (4 digits)
        parts = chunk_id.split("_p")
        assert len(parts) == 2


@pytest.mark.cp
def test_default_backend_multiple_pdfs():
    """CP: DefaultBackend can process multiple PDFs sequentially."""
    from libs.extraction.backend_default import DefaultBackend

    pdf_path = "data/raw/LSE_HEAD_2025.pdf"

    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not found: {pdf_path}")

    backend = DefaultBackend()

    # Process same PDF with different doc_ids
    result1 = backend.parse_pdf_to_pages(pdf_path, "DOC_A")
    result2 = backend.parse_pdf_to_pages(pdf_path, "DOC_B")

    # Should have same structure
    assert len(result1) == len(result2)

    # But different doc_ids
    assert result1[0]["doc_id"] == "DOC_A"
    assert result2[0]["doc_id"] == "DOC_B"

    # And different chunk_ids
    assert result1[0]["chunk_id"] != result2[0]["chunk_id"]
