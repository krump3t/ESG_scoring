"""
Phase 3: Redis Caching Module

In-memory LRU cache with TTL support. Falls back to pure Python when Redis unavailable.
Deterministic behavior with optional clock injection for testing.

Per SCA v13.8: Deterministic, explicit error handling, no external dependencies required.
"""

import logging
import os
import time
import hashlib
from typing import Any, Optional, Callable, Dict
from collections import OrderedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Feature flag to disable Redis (default: enabled if env var not set)
USE_REDIS = os.getenv("ESG_USE_REDIS", "1").lower() not in ("0", "false", "no")


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int
    misses: int
    sets: int
    gets: int
    evictions: int

    @property
    def hit_ratio(self) -> float:
        """Compute hit ratio [0, 1]."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class RedisCache:
    """
    Deterministic in-memory cache with LRU eviction and TTL support.

    Falls back to pure Python when Redis unavailable.
    Supports optional clock injection for deterministic testing.
    """

    def __init__(
        self,
        max_size: int = 100,
        default_ttl_seconds: Optional[int] = None,
        now_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        """
        Initialize cache.

        Args:
            max_size: Maximum number of items before LRU eviction (default: 100)
            default_ttl_seconds: Default TTL for all keys in seconds (default: None = no expiry)
            now_fn: Optional clock function for deterministic testing (default: time.time)
        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.now_fn = now_fn or time.time

        # In-memory storage: key -> (value, expires_at)
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        # Statistics
        self._stats = CacheStats(hits=0, misses=0, sets=0, gets=0, evictions=0)

        logger.info(
            f"RedisCache initialized: max_size={max_size}, "
            f"default_ttl={default_ttl_seconds}s, "
            f"use_redis={USE_REDIS}"
        )

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key (will be hashed if too long)

        Returns:
            Cached value or None if not found/expired

        Raises:
            ValueError: If key is empty
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("key cannot be empty")

        normalized_key = self._normalize_key(key)
        self._stats.gets += 1

        # Check if key exists
        if normalized_key not in self._cache:
            self._stats.misses += 1
            return None

        # Check if expired
        entry = self._cache[normalized_key]
        expires_at = entry.get("expires_at")

        if expires_at is not None and self.now_fn() >= expires_at:
            # Expired; remove and return None
            del self._cache[normalized_key]
            self._stats.misses += 1
            return None

        # Hit! Move to end (LRU order)
        self._cache.move_to_end(normalized_key)
        self._stats.hits += 1
        return entry["value"]

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (can be any picklable type)
            ttl_seconds: Time-to-live in seconds (default: use instance default)

        Raises:
            ValueError: If key empty or ttl_seconds invalid
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("key cannot be empty")

        # Validate TTL
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        if ttl is not None and ttl <= 0:
            raise ValueError(f"ttl_seconds must be > 0, got {ttl}")

        normalized_key = self._normalize_key(key)

        # Compute expiry time
        expires_at: Optional[float] = None
        if ttl is not None:
            expires_at = self.now_fn() + ttl

        # Store entry
        self._cache[normalized_key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": self.now_fn(),
        }

        # Move to end (most recently used)
        self._cache.move_to_end(normalized_key)
        self._stats.sets += 1

        # Evict LRU item if over capacity
        while len(self._cache) > self.max_size:
            # Pop oldest (first) item
            self._cache.popitem(last=False)
            self._stats.evictions += 1

        logger.debug(f"Cached key={key[:20]}..., ttl={ttl}s, size={len(self._cache)}")

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted, False otherwise

        Raises:
            ValueError: If key is empty
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("key cannot be empty")

        normalized_key = self._normalize_key(key)

        if normalized_key in self._cache:
            del self._cache[normalized_key]
            logger.debug(f"Deleted key={key[:20]}...")
            return True

        return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        self._cache.clear()
        self._stats = CacheStats(hits=0, misses=0, sets=0, gets=0, evictions=0)
        logger.info("Cache cleared")

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with keys: hits, misses, sets, gets, evictions, hit_ratio, size
        """
        return {
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "sets": self._stats.sets,
            "gets": self._stats.gets,
            "evictions": self._stats.evictions,
            "hit_ratio": round(self._stats.hit_ratio, 4),
            "size": len(self._cache),
            "max_size": self.max_size,
        }

    def _normalize_key(self, key: str) -> str:
        """
        Normalize cache key.

        For very long keys (>100 chars), hash to stay within reasonable limits.

        Args:
            key: Original key

        Returns:
            Normalized key (may be hashed)
        """
        if len(key) <= 100:
            return key

        # Hash long keys to keep them bounded
        return f"h:{hashlib.sha256(key.encode()).hexdigest()[:16]}"

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: Optional[int] = None,
    ) -> Any:
        """
        Get value from cache or compute if missing.

        Pattern: if key exists and not expired, return cached value;
        otherwise call compute_fn, cache result, and return.

        Args:
            key: Cache key
            compute_fn: Function to call if cache miss (takes no args)
            ttl_seconds: TTL for computed value

        Returns:
            Cached or computed value

        Raises:
            ValueError: If key is empty or ttl invalid
            RuntimeError: If compute_fn raises
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("key cannot be empty")

        # Try cache first
        cached = self.get(key)
        if cached is not None:
            return cached

        # Cache miss; compute
        try:
            value = compute_fn()
            self.set(key, value, ttl_seconds)
            return value
        except Exception as e:
            logger.error(f"compute_fn failed for key={key}: {e}")
            raise RuntimeError(f"Computation failed: {e}") from e
