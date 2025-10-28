"""Deterministic time abstraction for reproducible testing.

SCA mandate: every pipeline run must be timestamp-stable.  This module exposes a
single clock whose readings come from a fixed Unix timestamp.  The value is
resolved once from the environment (``FIXED_TIME``) or a protocol default and
then reused, ensuring identical outputs across runs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

DEFAULT_FIXED_TIME = 1_700_000_000.0  # 2023-11-14T22:13:20Z


@dataclass(frozen=True)
class Clock:
    """Clock with immutable timestamp readings."""

    fixed_time: float

    def now(self) -> datetime:
        """Return a timezone-aware datetime derived from ``fixed_time``."""
        return datetime.fromtimestamp(self.fixed_time, tz=timezone.utc)

    def time(self) -> float:
        """Return the deterministic Unix timestamp."""
        return self.fixed_time


_global_clock: Optional[Clock] = None


def _resolve_fixed_time() -> float:
    """Resolve the fixed timestamp from environment or protocol default."""
    raw = os.environ.get("FIXED_TIME")
    if raw is None:
        return DEFAULT_FIXED_TIME
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"FIXED_TIME must be numeric, got {raw!r}") from exc


def get_clock() -> Clock:
    """Return the process-wide deterministic clock instance."""
    global _global_clock
    resolved = _resolve_fixed_time()
    if _global_clock is None or _global_clock.fixed_time != resolved:
        _global_clock = Clock(fixed_time=resolved)
    return _global_clock


def set_clock(clock: Clock) -> None:
    """Override the global clock (primarily for tests)."""
    global _global_clock
    _global_clock = clock
