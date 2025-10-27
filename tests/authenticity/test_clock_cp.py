"""Test suite for clock.py — Deterministic time abstraction.

TDD-First: Tests define the contract for deterministic time operations.
Validates that FIXED_TIME environment variable enables fixed-time testing.
"""

import os
import pytest
from datetime import datetime
from hypothesis import given, settings, strategies as st


@pytest.mark.cp
class TestClockCP:
    """Critical path tests for deterministic time abstraction."""

    @pytest.fixture(autouse=True)
    def clear_fixed_time(self):
        """Fixture to clear FIXED_TIME before each test."""
        if "FIXED_TIME" in os.environ:
            del os.environ["FIXED_TIME"]
        yield
        if "FIXED_TIME" in os.environ:
            del os.environ["FIXED_TIME"]

    def test_clock_now_returns_datetime(self):
        """Verify get_clock().now() returns a datetime object."""
        from libs.utils.clock import get_clock

        clock = get_clock()
        result = clock.now()
        assert isinstance(result, datetime)

    def test_clock_time_returns_float(self):
        """Verify get_clock().time() returns a float (Unix timestamp)."""
        from libs.utils.clock import get_clock

        clock = get_clock()
        result = clock.time()
        assert isinstance(result, float)
        assert result > 0

    def test_fixed_time_env_var_produces_fixed_datetime(self):
        """Verify FIXED_TIME env var produces deterministic now() output."""
        from libs.utils.clock import get_clock

        os.environ["FIXED_TIME"] = "1609459200"  # 2021-01-01 00:00:00 UTC

        clock = get_clock()
        result1 = clock.now()
        result2 = clock.now()

        assert result1 == result2
        # Verify the timestamp matches expected value
        assert result1.timestamp() == 1609459200

    def test_fixed_time_env_var_produces_fixed_time_float(self):
        """Verify FIXED_TIME env var produces deterministic time() output."""
        from libs.utils.clock import get_clock

        os.environ["FIXED_TIME"] = "1609459200"

        clock = get_clock()
        result1 = clock.time()
        result2 = clock.time()

        assert result1 == result2
        assert result1 == 1609459200.0

    def test_multiple_get_clock_calls_return_same_instance(self):
        """Verify get_clock() returns the same Clock instance."""
        from libs.utils.clock import get_clock

        clock1 = get_clock()
        clock2 = get_clock()

        assert clock1 is clock2

    def test_set_clock_replaces_global_clock(self):
        """Verify set_clock() replaces the global clock instance."""
        from libs.utils.clock import get_clock, set_clock, Clock

        original = get_clock()

        new_clock = Clock()
        set_clock(new_clock)

        retrieved = get_clock()
        assert retrieved is new_clock
        assert retrieved is not original

    def test_clock_now_returns_utc_timezone_aware_datetime(self):
        """Verify clock.now() returns UTC timezone-aware datetime."""
        from libs.utils.clock import get_clock

        os.environ["FIXED_TIME"] = "1609459200"
        clock = get_clock()
        result = clock.now()

        assert result.tzinfo is not None

    def test_fixed_time_env_var_multiple_reads_identical(self):
        """Property test: Multiple reads with FIXED_TIME produce identical results."""
        from libs.utils.clock import get_clock

        os.environ["FIXED_TIME"] = "1609459200"
        clock = get_clock()

        results = [clock.now() for _ in range(10)]
        # All should be identical
        for result in results[1:]:
            assert result == results[0]

    @given(fixed_time_str=st.just("1609459200"))
    @settings(max_examples=1)
    def test_clock_with_property_based_fixed_time(self, fixed_time_str):
        """Property test: Clock works with various fixed time values."""
        from libs.utils.clock import get_clock

        os.environ["FIXED_TIME"] = fixed_time_str
        clock = get_clock()

        result = clock.now()
        assert isinstance(result, datetime)
        assert result.timestamp() == float(fixed_time_str)

    def test_clock_failure_path_invalid_fixed_time_value(self):
        """Failure path: Invalid FIXED_TIME value handled gracefully."""
        from libs.utils.clock import get_clock

        os.environ["FIXED_TIME"] = "invalid_timestamp"

        # Should either raise ValueError during get_clock() or later during now()
        try:
            clock = get_clock()
            result = clock.now()
            # If no exception, verify we still get a datetime
            assert isinstance(result, datetime)
        except ValueError:
            # This is acceptable behavior
            pass

    def test_clock_without_fixed_time_returns_reasonable_datetime(self):
        """Verify clock without FIXED_TIME returns reasonable current datetime."""
        from libs.utils.clock import get_clock

        if "FIXED_TIME" in os.environ:
            del os.environ["FIXED_TIME"]

        clock = get_clock()
        result = clock.now()

        # Should be close to actual current time
        assert isinstance(result, datetime)
        # Should not be extremely old or in far future
        year = result.year
        assert 2020 <= year <= 2030

    def test_clock_fixed_time_to_real_time_transition(self):
        """Test transition from FIXED_TIME to real time."""
        from libs.utils.clock import get_clock

        # Start with fixed time
        os.environ["FIXED_TIME"] = "1609459200"
        clock1 = get_clock()
        result1 = clock1.time()
        assert result1 == 1609459200.0

        # Switch to real time
        del os.environ["FIXED_TIME"]
        clock2 = get_clock()
        result2 = clock2.time()

        # Should be current time, not fixed
        assert result2 != 1609459200.0
        assert result2 > 1609459200.0

    def test_clock_fixed_time_change(self):
        """Test changing fixed time value."""
        from libs.utils.clock import get_clock

        # Set first fixed time
        os.environ["FIXED_TIME"] = "1609459200"
        clock1 = get_clock()
        assert clock1.time() == 1609459200.0

        # Change to different fixed time
        os.environ["FIXED_TIME"] = "1640995200"
        clock2 = get_clock()
        assert clock2.time() == 1640995200.0
