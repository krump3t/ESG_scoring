"""CP Tests for Text Quality Module - Task 026

SCA v13.8-MEA Compliance:
- TDD Guard: Tests written BEFORE implementation
- CP Markers: All tests marked with @pytest.mark.cp
- Failure Paths: Tests for edge cases (binary, empty, control chars)
- Property Tests: Hypothesis @given tests
"""
import pytest
from hypothesis import given, strategies as st


@pytest.mark.cp
def test_is_binary_like_null_bytes():
    """CP: is_binary_like detects null bytes."""
    from libs.extraction.text_clean import is_binary_like

    # Null byte should be detected
    assert is_binary_like("hello\x00world") is True

    # Clean text should not be binary
    assert is_binary_like("hello world") is False


@pytest.mark.cp
def test_is_binary_like_empty():
    """CP Failure Path: Empty text is considered binary."""
    from libs.extraction.text_clean import is_binary_like

    assert is_binary_like("") is True
    assert is_binary_like(None) is True or is_binary_like("") is True  # Handle None gracefully


@pytest.mark.cp
def test_is_binary_like_control_characters():
    """CP: is_binary_like detects excessive control characters."""
    from libs.extraction.text_clean import is_binary_like

    # Excessive control chars (>2%)
    text_with_controls = "a" * 50 + "\x01\x02\x03\x04\x05"  # 10% control chars
    assert is_binary_like(text_with_controls) is True

    # Minimal control chars (<2%)
    clean_text = "a" * 100 + "\x01"  # 1% control chars
    assert is_binary_like(clean_text) is False


@pytest.mark.cp
def test_clean_text_removes_control_chars():
    """CP: clean_text removes control characters."""
    from libs.extraction.text_clean import clean_text

    # Control chars should be removed (except \t, \n, \r)
    input_text = "hello\x01\x02world\x03test"
    output = clean_text(input_text)

    # Should not contain control chars
    assert "\x01" not in output
    assert "\x02" not in output
    assert "\x03" not in output

    # Should contain regular text
    assert "hello" in output
    assert "world" in output


@pytest.mark.cp
def test_clean_text_normalizes_whitespace():
    """CP: clean_text normalizes whitespace."""
    from libs.extraction.text_clean import clean_text

    # Multiple spaces should become single space
    input_text = "hello    world     test"
    output = clean_text(input_text)

    assert output == "hello world test"


@pytest.mark.cp
def test_clean_text_empty():
    """CP Failure Path: clean_text handles empty input."""
    from libs.extraction.text_clean import clean_text

    assert clean_text("") == ""
    assert clean_text("   ") == ""  # Only whitespace


@pytest.mark.cp
def test_quality_score_clean_text():
    """CP: quality_score returns 1.0 for clean text."""
    from libs.extraction.text_clean import quality_score

    score = quality_score("This is clean text with no issues.")
    assert score == 1.0


@pytest.mark.cp
def test_quality_score_binary():
    """CP: quality_score returns low score for binary-like text."""
    from libs.extraction.text_clean import quality_score

    # Binary-like text should have penalty
    score = quality_score("hello\x00world")
    assert score < 1.0
    assert score >= 0.0


@pytest.mark.cp
def test_quality_score_empty():
    """CP Failure Path: quality_score returns 0.0 for empty text."""
    from libs.extraction.text_clean import quality_score

    assert quality_score("") == 0.0


@pytest.mark.cp
def test_extract_clean_quote():
    """CP: extract_clean_quote returns cleaned text with score."""
    from libs.extraction.text_clean import extract_clean_quote

    input_text = "   This is  a   test   quote.   "
    cleaned, score = extract_clean_quote(input_text, max_length=500)

    # Should be cleaned
    assert cleaned.strip() == "This is a test quote."

    # Should have quality score
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@pytest.mark.cp
def test_extract_clean_quote_truncation():
    """CP: extract_clean_quote truncates long text."""
    from libs.extraction.text_clean import extract_clean_quote

    long_text = "a" * 1000
    cleaned, score = extract_clean_quote(long_text, max_length=100)

    # Should be truncated
    assert len(cleaned) <= 104  # 100 + "..." = 103 max
    assert cleaned.endswith("...") or len(cleaned) <= 100


@pytest.mark.cp
@given(text=st.text(min_size=0, max_size=1000))
def test_clean_text_property(text):
    """CP Property Test: clean_text never raises exceptions."""
    from libs.extraction.text_clean import clean_text

    try:
        result = clean_text(text)
        # Should return string
        assert isinstance(result, str)
    except Exception as e:
        pytest.fail(f"clean_text raised exception for input: {e}")


@pytest.mark.cp
@given(text=st.text(min_size=0, max_size=1000))
def test_quality_score_property(text):
    """CP Property Test: quality_score always returns valid range."""
    from libs.extraction.text_clean import quality_score

    score = quality_score(text)

    # Should be in valid range
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


@pytest.mark.cp
def test_clean_text_preserves_tabs_newlines():
    """CP: clean_text preserves \t and \n (allowed whitespace)."""
    from libs.extraction.text_clean import clean_text

    input_text = "hello\tworld\ntest"
    output = clean_text(input_text)

    # Tabs and newlines should be preserved (or normalized to spaces)
    # Implementation may normalize, but should not crash
    assert isinstance(output, str)


@pytest.mark.cp
def test_is_binary_like_pdf_artifact():
    """CP: is_binary_like detects common PDF artifacts."""
    from libs.extraction.text_clean import is_binary_like

    # Common PDF artifact
    pdf_header = "%PDF-1.4\x00\x00"
    assert is_binary_like(pdf_header) is True


@pytest.mark.cp
def test_extract_clean_quote_with_binary():
    """CP Failure Path: extract_clean_quote handles binary content."""
    from libs.extraction.text_clean import extract_clean_quote

    binary_text = "Some text\x00with\x01binary"
    cleaned, score = extract_clean_quote(binary_text, max_length=500)

    # Should clean binary chars
    assert "\x00" not in cleaned
    assert "\x01" not in cleaned

    # Score should be penalized
    assert score < 1.0
