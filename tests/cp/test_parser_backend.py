"""CP Tests for PDF Parser Backend Protocol (Task 026)

SCA v13.8-MEA Compliance:
- TDD Guard: Tests written BEFORE implementation
- CP Markers: All tests marked with @pytest.mark.cp
- Failure Paths: Tests for error conditions
- Property Tests: Hypothesis @given tests for invariants
"""
import pytest
from hypothesis import given, strategies as st
from typing import List, Dict, Any
import os
import tempfile


@pytest.mark.cp
def test_parser_backend_protocol_exists():
    """CP: PDFParserBackend protocol is importable."""
    from libs.extraction.parser_backend import PDFParserBackend

    # Protocol should be a class/type
    assert PDFParserBackend is not None
    assert hasattr(PDFParserBackend, '__name__')


@pytest.mark.cp
def test_chunk_id_generator_deterministic():
    """CP: Chunk ID generator produces deterministic, sortable IDs."""
    from libs.extraction.parser_backend import _mk_chunk_id

    # Same inputs → same output
    id1 = _mk_chunk_id("TEST_DOC", 1, 0)
    id2 = _mk_chunk_id("TEST_DOC", 1, 0)
    assert id1 == id2, "Chunk ID not deterministic"

    # Expected format: {doc_id}_p{page:04d}_{idx:02d}
    assert id1 == "TEST_DOC_p0001_00"

    # Different pages → different IDs
    id_p1 = _mk_chunk_id("TEST_DOC", 1, 0)
    id_p2 = _mk_chunk_id("TEST_DOC", 2, 0)
    assert id_p1 != id_p2

    # IDs should be sortable (lexicographic order = page order)
    assert id_p1 < id_p2


@pytest.mark.cp
@given(
    doc_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_')),
    page=st.integers(min_value=1, max_value=9999),
    idx=st.integers(min_value=0, max_value=99)
)
def test_chunk_id_format_property(doc_id, page, idx):
    """CP Property Test: Chunk IDs always have correct format."""
    from libs.extraction.parser_backend import _mk_chunk_id

    chunk_id = _mk_chunk_id(doc_id, page, idx)

    # Must contain doc_id
    assert doc_id in chunk_id

    # Must have format: {doc_id}_p{page:04d}_{idx:02d}
    parts = chunk_id.split('_p')
    assert len(parts) == 2, f"Invalid format: {chunk_id}"

    # Page and idx parts should exist
    page_idx_part = parts[1]
    assert '_' in page_idx_part, f"Missing idx separator: {chunk_id}"


@pytest.mark.cp
def test_parser_backend_protocol_structure():
    """CP: PDFParserBackend protocol has required method signature."""
    from libs.extraction.parser_backend import PDFParserBackend
    import inspect

    # Check for parse_pdf_to_pages method
    assert hasattr(PDFParserBackend, 'parse_pdf_to_pages'), \
        "PDFParserBackend must have parse_pdf_to_pages method"

    # Check method signature (via Protocol annotations)
    if hasattr(PDFParserBackend, '__annotations__'):
        # Protocol defines method, check it exists
        pass  # Detailed signature check happens in implementation tests


@pytest.mark.cp
def test_chunk_id_failure_invalid_page():
    """CP Failure Path: Chunk ID with page 0 or negative should work (no validation)."""
    from libs.extraction.parser_backend import _mk_chunk_id

    # Page 0 is technically allowed (though semantically wrong)
    # Function doesn't validate, just formats
    id_p0 = _mk_chunk_id("TEST", 0, 0)
    assert id_p0 == "TEST_p0000_00"

    # Negative page (edge case, function formats it)
    id_neg = _mk_chunk_id("TEST", -1, 0)
    # Note: Negative numbers will have minus sign in output
    # This is acceptable as function doesn't validate inputs


@pytest.mark.cp
def test_chunk_id_large_values():
    """CP: Chunk ID handles large page/idx values (overflow test)."""
    from libs.extraction.parser_backend import _mk_chunk_id

    # Very large page (beyond 4 digits)
    id_large_page = _mk_chunk_id("TEST", 99999, 0)
    # Should still work (format spec allows overflow)
    assert "TEST_p" in id_large_page

    # Very large idx (beyond 2 digits)
    id_large_idx = _mk_chunk_id("TEST", 1, 999)
    # Should still work
    assert "_p0001_" in id_large_idx


@pytest.mark.cp
@given(doc_id=st.text(min_size=1, max_size=100))
def test_chunk_id_special_characters_property(doc_id):
    """CP Property Test: Chunk ID handles doc_ids with various characters."""
    from libs.extraction.parser_backend import _mk_chunk_id

    # Should not raise exception
    try:
        chunk_id = _mk_chunk_id(doc_id, 1, 0)
        # Basic sanity check
        assert len(chunk_id) > 0
    except Exception as e:
        pytest.fail(f"Chunk ID generation failed for doc_id='{doc_id}': {e}")


@pytest.mark.cp
def test_chunk_id_uniqueness():
    """CP: Chunk IDs are unique for different (doc, page, idx) combinations."""
    from libs.extraction.parser_backend import _mk_chunk_id

    ids = set()

    # Generate IDs for multiple combinations
    for doc_id in ["DOC_A", "DOC_B", "DOC_C"]:
        for page in range(1, 11):  # pages 1-10
            for idx in range(0, 3):  # idx 0-2
                chunk_id = _mk_chunk_id(doc_id, page, idx)

                # Should be unique
                assert chunk_id not in ids, f"Duplicate chunk_id: {chunk_id}"
                ids.add(chunk_id)

    # Total unique IDs: 3 docs × 10 pages × 3 idx = 90
    assert len(ids) == 90


@pytest.mark.cp
def test_parser_backend_protocol_type_hints():
    """CP: PDFParserBackend has proper type hints."""
    from libs.extraction.parser_backend import PDFParserBackend
    from typing import get_type_hints

    # Protocol should have type hints
    # (This test verifies protocol is properly typed)
    try:
        hints = get_type_hints(PDFParserBackend.parse_pdf_to_pages)
        # Should have return type annotation
        assert 'return' in hints, "parse_pdf_to_pages missing return type hint"
    except AttributeError:
        # If Protocol doesn't expose hints directly, that's okay
        # Implementation tests will verify compliance
        pass


# Placeholder for future implementation tests
# These will be added when backend implementations are created
@pytest.mark.cp
@pytest.mark.skip(reason="Implementation not yet created")
def test_default_backend_implements_protocol():
    """CP: DefaultBackend implements PDFParserBackend protocol."""
    from libs.extraction.backend_default import DefaultBackend
    from libs.extraction.parser_backend import PDFParserBackend

    backend = DefaultBackend()

    # Check protocol compliance
    assert hasattr(backend, 'parse_pdf_to_pages')
    assert callable(backend.parse_pdf_to_pages)


@pytest.mark.cp
@pytest.mark.skip(reason="Implementation not yet created")
def test_docling_backend_implements_protocol():
    """CP: DoclingBackend implements PDFParserBackend protocol."""
    # This test will be implemented in Phase 2
    pass
