"""
Comprehensive Test Suite for SourceRef Enhancements (Phase 2)

**TDD Approach**: These tests are written BEFORE implementing SourceRef.priority_score field.
**SCA v13.8 Compliance**:
- ≥1 test marked @pytest.mark.cp
- ≥2 Hypothesis property tests
- ≥3 failure-path tests
- ≥95% coverage target on SourceRef model

**Test Focus**: SourceRef.priority_score field validation
- Range validation: [0, 100]
- Default value: 100 (lowest priority)
- Immutability: frozen=True
- Type safety: int only

Total: 10 tests
"""

import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError

# Import from Phase 2 implementation
try:
    from libs.contracts.ingestion_contracts import SourceRef, CompanyRef, CompanyReport
except ImportError as e:
    pytestmark = pytest.mark.skip(reason=f"Implementation not yet available - TDD mode: {e}")


# ============================================================================
# UNIT TESTS (SourceRef Validation)
# ============================================================================

@pytest.mark.cp
def test_source_ref_accepts_valid_priority_score():
    """Test that SourceRef accepts priority_score in valid range [0, 100]."""
    # Arrange & Act: Valid scores
    source_ref_0 = SourceRef(
        provider="test",
        tier=1,
        content_type="application/pdf",
        priority_score=0  # Best priority
    )

    source_ref_50 = SourceRef(
        provider="test",
        tier=1,
        content_type="application/pdf",
        priority_score=50  # Mid priority
    )

    source_ref_100 = SourceRef(
        provider="test",
        tier=1,
        content_type="application/pdf",
        priority_score=100  # Worst priority
    )

    # Assert: All created successfully
    assert source_ref_0.priority_score == 0
    assert source_ref_50.priority_score == 50
    assert source_ref_100.priority_score == 100


@pytest.mark.cp
def test_source_ref_defaults_priority_score_to_100():
    """Test that SourceRef defaults priority_score to 100 if not specified."""
    # Arrange & Act: Create without priority_score
    source_ref = SourceRef(
        provider="test",
        tier=1,
        content_type="application/pdf"
    )

    # Assert: Defaults to 100 (lowest priority)
    assert source_ref.priority_score == 100


@pytest.mark.cp
def test_source_ref_validates_tier_range():
    """Test that SourceRef validates tier is in range [1, 3]."""
    # Valid tiers
    for tier in [1, 2, 3]:
        source_ref = SourceRef(
            provider="test",
            tier=tier,
            content_type="application/pdf",
            priority_score=50
        )
        assert source_ref.tier == tier

    # Invalid tiers
    for invalid_tier in [0, 4, -1, 10]:
        with pytest.raises(ValidationError):
            SourceRef(
                provider="test",
                tier=invalid_tier,
                content_type="application/pdf",
                priority_score=50
            )


@pytest.mark.cp
def test_source_ref_is_immutable():
    """Test that SourceRef is immutable (frozen=True)."""
    # Arrange
    source_ref = SourceRef(
        provider="test",
        tier=1,
        content_type="application/pdf",
        priority_score=50
    )

    # Act & Assert: Attempting to mutate raises exception
    with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
        source_ref.priority_score = 10

    with pytest.raises(Exception):
        source_ref.tier = 2


@pytest.mark.cp
def test_source_ref_json_serialization():
    """Test that SourceRef can be serialized to/from JSON."""
    # Arrange
    source_ref = SourceRef(
        provider="sec_edgar",
        tier=1,
        url="https://www.sec.gov/Archives/edgar/data/320193/file.htm",
        content_type="text/html",
        priority_score=20
    )

    # Act: Serialize to JSON
    json_data = source_ref.model_dump()

    # Assert: JSON contains all fields
    assert json_data["provider"] == "sec_edgar"
    assert json_data["tier"] == 1
    assert json_data["priority_score"] == 20
    assert json_data["content_type"] == "text/html"

    # Act: Deserialize from JSON
    deserialized = SourceRef(**json_data)

    # Assert: Round-trip successful
    assert deserialized == source_ref


# ============================================================================
# FAILURE-PATH TESTS
# ============================================================================

@pytest.mark.cp
def test_source_ref_rejects_negative_priority_score():
    """Failure path: SourceRef rejects priority_score < 0."""
    # Act & Assert: Negative score raises ValidationError
    with pytest.raises(ValidationError, match="priority_score"):
        SourceRef(
            provider="test",
            tier=1,
            content_type="application/pdf",
            priority_score=-1
        )


@pytest.mark.cp
def test_source_ref_rejects_priority_score_above_100():
    """Failure path: SourceRef rejects priority_score > 100."""
    # Act & Assert: Score above 100 raises ValidationError
    with pytest.raises(ValidationError, match="priority_score"):
        SourceRef(
            provider="test",
            tier=1,
            content_type="application/pdf",
            priority_score=101
        )


@pytest.mark.cp
def test_source_ref_rejects_non_integer_priority_score():
    """Failure path: SourceRef rejects non-integer priority_score."""
    # Act & Assert: Float raises ValidationError (coercion may occur, depends on Pydantic config)
    with pytest.raises(ValidationError):
        SourceRef(
            provider="test",
            tier=1,
            content_type="application/pdf",
            priority_score="not an integer"  # String instead of int
        )


@pytest.mark.cp
def test_source_ref_requires_provider_field():
    """Failure path: SourceRef requires provider field (cannot be None or empty)."""
    # Act & Assert: Missing provider raises ValidationError
    with pytest.raises(ValidationError):
        SourceRef(
            tier=1,
            content_type="application/pdf",
            priority_score=50
        )


@pytest.mark.cp
def test_source_ref_requires_content_type_field():
    """Failure path: SourceRef requires content_type field."""
    # Act & Assert: Missing content_type raises ValidationError
    with pytest.raises(ValidationError):
        SourceRef(
            provider="test",
            tier=1,
            priority_score=50
        )


# ============================================================================
# PROPERTY-BASED TESTS (Hypothesis)
# ============================================================================

@pytest.mark.cp
@pytest.mark.hypothesis
@given(st.integers(min_value=0, max_value=100))
@settings(max_examples=100, deadline=2000)
def test_source_ref_accepts_all_valid_priority_scores(priority_score):
    """Property test: SourceRef accepts ANY integer in [0, 100]."""
    # Act
    source_ref = SourceRef(
        provider="test",
        tier=1,
        content_type="application/pdf",
        priority_score=priority_score
    )

    # Assert: Created successfully with correct value
    assert source_ref.priority_score == priority_score
    assert 0 <= source_ref.priority_score <= 100


@pytest.mark.cp
@pytest.mark.hypothesis
@given(st.integers().filter(lambda x: x < 0 or x > 100))
@settings(max_examples=100, deadline=2000)
def test_source_ref_rejects_all_invalid_priority_scores(invalid_score):
    """Property test: SourceRef rejects ANY integer outside [0, 100]."""
    # Act & Assert: Invalid scores raise ValidationError
    with pytest.raises(ValidationError):
        SourceRef(
            provider="test",
            tier=1,
            content_type="application/pdf",
            priority_score=invalid_score
        )


# ============================================================================
# Test Summary
# ============================================================================
"""
Test Coverage Summary (SourceRef Enhancements - Phase 2):

Unit Tests (5):
✅ test_source_ref_accepts_valid_priority_score
✅ test_source_ref_defaults_priority_score_to_100
✅ test_source_ref_validates_tier_range
✅ test_source_ref_is_immutable
✅ test_source_ref_json_serialization

Failure-Path Tests (5):
✅ test_source_ref_rejects_negative_priority_score
✅ test_source_ref_rejects_priority_score_above_100
✅ test_source_ref_rejects_non_integer_priority_score
✅ test_source_ref_requires_provider_field
✅ test_source_ref_requires_content_type_field

Property Tests (2):
✅ test_source_ref_accepts_all_valid_priority_scores (Hypothesis)
✅ test_source_ref_rejects_all_invalid_priority_scores (Hypothesis)

Total: 12 tests

SCA v13.8 Compliance:
✅ All tests marked @pytest.mark.cp
✅ ≥2 Hypothesis property tests
✅ ≥3 failure-path tests
✅ Tests written BEFORE implementation (TDD)
✅ Coverage target: ≥95% on SourceRef model

Priority Score Specification:
- Range: [0, 100] (inclusive)
- Lower = Better (0 = highest priority, 100 = lowest)
- Default: 100 (if not specified)
- Type: int (strictly validated)
- Immutable: Cannot be changed after creation (frozen=True)

Examples:
- SourceRef(tier=1, priority_score=5) → SEC XBRL JSON (structured data)
- SourceRef(tier=1, priority_score=10) → SEC 10-K PDF
- SourceRef(tier=1, priority_score=20) → SEC 10-K HTML
- SourceRef(tier=2, priority_score=30) → GRI database PDF
- SourceRef(tier=3, priority_score=50) → Company IR site PDF
"""
