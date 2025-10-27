"""Deterministic time abstraction for reproducible testing.

Provides Clock class that respects FIXED_TIME environment variable for fixed-time testing.
Enables deterministic behavior while maintaining wall-clock fallback for production.

Usage:
    from libs.utils.clock import get_clock

    clock = get_clock()
    now = clock.now()  # datetime object
    timestamp = clock.time()  # Unix timestamp (float)

Environment Variables:
    FIXED_TIME: Unix timestamp (float) for deterministic testing
               If set, all time calls return this fixed value.
               If not set, uses real wall-clock time.
"""

import os
from datetime import datetime, timezone
from typing import Optional


class Clock:
    """Deterministic time provider supporting both fixed and real time."""

    def __init__(self, fixed_time: Optional[float] = None):
        """Initialize Clock with optional fixed time.

        Args:
            fixed_time: Unix timestamp (float) for deterministic testing.
                       If None, uses real wall-clock time.
        """
        self.fixed_time = fixed_time

    def now(self) -> datetime:
        """Return current datetime (UTC, timezone-aware).

        Returns:
            Timezone-aware datetime in UTC.
            If FIXED_TIME is set, returns datetime for that timestamp.
            Otherwise, returns current wall-clock datetime.
        """
        if self.fixed_time is not None:
            return datetime.fromtimestamp(self.fixed_time, tz=timezone.utc)
        return datetime.now(tz=timezone.utc)

    def time(self) -> float:
        """Return current Unix timestamp (seconds since epoch).

        Returns:
            Float Unix timestamp.
            If FIXED_TIME is set, returns that value.
            Otherwise, returns current wall-clock timestamp.
        """
        if self.fixed_time is not None:
            return float(self.fixed_time)
        return datetime.now(tz=timezone.utc).timestamp()


# Global clock instance
_global_clock: Clock = Clock()


def get_clock() -> Clock:
    """Get the global clock instance.

    Respects FIXED_TIME environment variable.
    Caches the instance so repeated calls return the same object.

    Returns:
        Global Clock instance configured from environment.

    Environment Variables:
        FIXED_TIME: Unix timestamp for deterministic testing
    """
    global _global_clock

    # Check if FIXED_TIME is set
    fixed_time_str = os.environ.get("FIXED_TIME")

    # Only create a new Clock if the current one doesn't match the environment
    if isinstance(_global_clock, Clock):
        # If the current clock is a real-time clock and FIXED_TIME is now set,
        # or if FIXED_TIME has changed, update it
        current_fixed_time = _global_clock.fixed_time
        if fixed_time_str is not None:
            try:
                new_fixed_time = float(fixed_time_str)
                if current_fixed_time != new_fixed_time:
                    _global_clock = Clock(fixed_time=new_fixed_time)
            except ValueError:
                raise ValueError(
                    f"FIXED_TIME must be a valid float, got: {fixed_time_str}"
                )
        elif current_fixed_time is not None:
            # FIXED_TIME was set but is now unset
            _global_clock = Clock()

    return _global_clock


def set_clock(clock: Clock) -> None:
    """Set the global clock instance (primarily for testing).

    Args:
        clock: Clock instance to use globally.
    """
    global _global_clock
    _global_clock = clock
