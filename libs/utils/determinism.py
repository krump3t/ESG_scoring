"""Seeded randomness utilities for deterministic pseudo-random number generation.

Provides factory functions for creating seeded random.Random instances.
Respects SEED and PYTHONHASHSEED environment variables for reproducibility.

Usage:
    from libs.utils.determinism import get_seeded_random, set_seed

    # Get seeded random instance
    rng = get_seeded_random()
    random_val = rng.random()  # Deterministic if SEED is set

    # Set seed explicitly
    set_seed(42)
    rng = get_seeded_random()

Environment Variables:
    SEED: Integer seed value for seeded randomness.
         If set, all random calls are deterministic.
         If not set, uses unseeded randomness.
    PYTHONHASHSEED: Global hash randomization seed (should be 0 for reproducibility).
"""

import os
import random
from typing import Optional


# Global seed value
_global_seed: Optional[int] = None


def get_seeded_random() -> random.Random:
    """Get a seeded random.Random instance.

    Respects SEED environment variable.

    Returns:
        Seeded random.Random instance.
        If SEED env var is set, uses that as seed.
        If not set, uses unseeded randomness.

    Environment Variables:
        SEED: Integer seed for deterministic behavior
    """
    seed_str = os.environ.get("SEED")

    if seed_str is not None:
        try:
            seed = int(seed_str)
        except ValueError:
            raise ValueError(f"SEED must be a valid integer, got: {seed_str}")
    else:
        seed = None

    rng = random.Random(seed)
    return rng


def set_seed(seed: int) -> None:
    """Set the global seed value and create a new seeded random instance.

    Updates the SEED environment variable and internal state.

    Args:
        seed: Integer seed value for deterministic randomness.
    """
    global _global_seed
    _global_seed = seed
    os.environ["SEED"] = str(seed)


def initialize_numpy_seed() -> None:
    """Initialize numpy seeding if numpy is available.

    Respects SEED environment variable for numpy.random consistency.
    Optional: only called if numpy is actually used in the pipeline.
    """
    try:
        import numpy as np

        seed_str = os.environ.get("SEED")
        if seed_str is not None:
            try:
                seed = int(seed_str)
                np.random.seed(seed)
            except ValueError:
                raise ValueError(f"SEED must be a valid integer, got: {seed_str}")
    except ImportError:
        # numpy not available; skip numpy seeding (optional dependency)
        # This is acceptable - numpy seeding only needed for numpy-based code
        pass  # @allow-silent:Optional dependency numpy not installed
