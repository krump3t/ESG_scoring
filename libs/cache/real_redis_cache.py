"""
Phase 4b: Real Redis Cache Implementation

Implements real Redis backend for ESG query result caching.
Replaces in-memory fallback with authentic redis-py client.

SCA v13.8 Compliance:
- Authentic Computation: Real Redis with network I/O (no mocks)
- Fail-Fast: RuntimeError if Redis unavailable (no silent degradation)
- Determinism: Consistent key hashing and TTL behavior
- Type Safety: 100% type hints with mypy --strict

Backend Details:
- Client: redis-py (official Python client)
- Protocol: RESP3
- Serialization: JSON (for query results)
- Eviction: Redis LRU (maxmemory-policy allkeys-lru)
"""

import logging
import hashlib
import json
from typing import Any, Optional, Callable, Dict
from dataclasses import dataclass
import redis

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics for monitoring hit ratio."""

    hits: int
    misses: int
    sets: int
    gets: int

    @property
    def hit_ratio(self) -> float:
        """Compute cache hit ratio [0, 1]."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class RealRedisCache:
    """
    Real Redis backend for ESG query result caching.

    Uses redis-py client for authentic distributed caching.
    Fail-fast if Redis unavailable (no fallback to in-memory).

    Attributes:
        host: Redis server hostname
        port: Redis server port
        max_size: Maximum cache size (for stats reporting)
        default_ttl_seconds: Default TTL for cached values
        redis_client: redis.Redis client instance
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        max_size: int = 100,
        default_ttl_seconds: Optional[int] = None,
        db: int = 0,
        decode_responses: bool = True
    ) -> None:
        """
        Initialize real Redis cache.

        Args:
            host: Redis server hostname (default: localhost)
            port: Redis server port (default: 6379)
            max_size: Maximum cache size (for stats, not enforced) (default: 100)
            default_ttl_seconds: Default TTL in seconds (default: None = no expiry)
            db: Redis database number (default: 0)
            decode_responses: Decode responses as UTF-8 strings (default: True)

        Raises:
            RuntimeError: If Redis connection fails (fail-fast)
        """
        self.host = host
        self.port = port
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds

        logger.info(
            f"Initializing RealRedisCache: host={host}, port={port}, "
            f"max_size={max_size}, default_ttl={default_ttl_seconds}s"
        )

        # Initialize Redis client
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Test connection (fail-fast if unavailable)
            if not self.redis_client.ping():
                raise ConnectionError("Redis PING failed")

            logger.info(f"Successfully connected to Redis: {host}:{port}")

        except (redis.ConnectionError, redis.TimeoutError, ConnectionError) as e:
            logger.error(f"Failed to connect to Redis at {host}:{port}: {e}")
            raise RuntimeError(f"Failed to connect to Redis at {host}:{port}: {e}") from e

        # Initialize stats (in-memory tracking)
        self._stats = CacheStats(hits=0, misses=0, sets=0, gets=0)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.

        Args:
            key: Cache key (will be normalized/hashed if long)

        Returns:
            Cached value (deserialized from JSON) or None if not found/expired

        Raises:
            ValueError: If key is empty
            RuntimeError: If Redis operation fails
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("key cannot be empty")

        normalized_key = self._normalize_key(key)
        self._stats.gets += 1

        try:
            # Get from Redis
            value_json = self.redis_client.get(normalized_key)

            if value_json is None:
                self._stats.misses += 1
                return None

            # Deserialize JSON
            value = json.loads(value_json)  # type: ignore[arg-type]
            self._stats.hits += 1

            logger.debug(f"Cache HIT: key={key[:20]}...")
            return value

        except redis.RedisError as e:
            logger.error(f"Redis GET failed for key={key}: {e}")
            raise RuntimeError(f"Redis GET failed: {e}") from e
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to deserialize cached value for key={key}: {e}")
            self._stats.misses += 1
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set value in Redis cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl_seconds: Time-to-live in seconds (default: use instance default)

        Raises:
            ValueError: If key empty or ttl_seconds invalid
            RuntimeError: If Redis operation fails
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("key cannot be empty")

        # Validate TTL
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        if ttl is not None and ttl <= 0:
            raise ValueError(f"ttl_seconds must be > 0, got {ttl}")

        normalized_key = self._normalize_key(key)

        try:
            # Serialize to JSON
            value_json = json.dumps(value)

            # Set in Redis with optional TTL
            if ttl is not None:
                self.redis_client.setex(normalized_key, ttl, value_json)
            else:
                self.redis_client.set(normalized_key, value_json)

            self._stats.sets += 1

            logger.debug(f"Cache SET: key={key[:20]}..., ttl={ttl}s")

        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value for key={key}: {e}")
            raise ValueError(f"Value not JSON-serializable: {e}") from e
        except redis.RedisError as e:
            logger.error(f"Redis SET failed for key={key}: {e}")
            raise RuntimeError(f"Redis SET failed: {e}") from e

    def delete(self, key: str) -> bool:
        """
        Delete key from Redis cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted, False otherwise

        Raises:
            ValueError: If key is empty
            RuntimeError: If Redis operation fails
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("key cannot be empty")

        normalized_key = self._normalize_key(key)

        try:
            deleted_count: int = self.redis_client.delete(normalized_key)  # type: ignore[assignment]

            logger.debug(f"Cache DELETE: key={key[:20]}..., deleted={deleted_count > 0}")
            return deleted_count > 0

        except redis.RedisError as e:
            logger.error(f"Redis DELETE failed for key={key}: {e}")
            raise RuntimeError(f"Redis DELETE failed: {e}") from e

    def clear(self) -> None:
        """
        Clear all entries from Redis cache (flushes entire DB).

        WARNING: This flushes the entire Redis database (db=0 by default).
        Use with caution in production.

        Raises:
            RuntimeError: If Redis operation fails
        """
        try:
            self.redis_client.flushdb()
            self._stats = CacheStats(hits=0, misses=0, sets=0, gets=0)

            logger.info("Cache cleared (Redis DB flushed)")

        except redis.RedisError as e:
            logger.error(f"Redis FLUSHDB failed: {e}")
            raise RuntimeError(f"Redis FLUSHDB failed: {e}") from e

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with keys: hits, misses, sets, gets, hit_ratio, size

        Raises:
            RuntimeError: If Redis operation fails
        """
        try:
            # Get current size from Redis
            size = self.redis_client.dbsize()

            return {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "sets": self._stats.sets,
                "gets": self._stats.gets,
                "hit_ratio": round(self._stats.hit_ratio, 4),
                "size": size,
                "max_size": self.max_size,
            }

        except redis.RedisError as e:
            logger.error(f"Redis DBSIZE failed: {e}")
            raise RuntimeError(f"Redis stats retrieval failed: {e}") from e

    def _normalize_key(self, key: str) -> str:
        """
        Normalize cache key for Redis.

        For very long keys (>100 chars), hash to stay within reasonable limits.

        Args:
            key: Original key

        Returns:
            Normalized key (may be hashed with 'h:' prefix)
        """
        if len(key) <= 100:
            return f"esg:{key}"  # Add namespace prefix

        # Hash long keys to keep them bounded
        return f"esg:h:{hashlib.sha256(key.encode()).hexdigest()[:16]}"

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """
        Get value from cache or compute if missing (read-through pattern).

        Pattern: if key exists, return cached value; otherwise call compute_fn,
        cache result, and return.

        Args:
            key: Cache key
            compute_fn: Function to call if cache miss (takes no args, returns JSON-serializable value)
            ttl_seconds: TTL for computed value (default: use instance default)

        Returns:
            Cached or computed value

        Raises:
            ValueError: If key is empty or ttl invalid
            RuntimeError: If compute_fn raises or Redis fails
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


def create_cache(
    host: str = "localhost",
    port: int = 6379,
    default_ttl_seconds: Optional[int] = 300
) -> RealRedisCache:
    """
    Factory function to create RealRedisCache.

    Args:
        host: Redis server hostname (default: localhost)
        port: Redis server port (default: 6379)
        default_ttl_seconds: Default TTL in seconds (default: 300 = 5 minutes)

    Returns:
        Initialized RealRedisCache instance

    Raises:
        RuntimeError: If Redis connection fails
    """
    return RealRedisCache(
        host=host,
        port=port,
        max_size=100,
        default_ttl_seconds=default_ttl_seconds
    )
