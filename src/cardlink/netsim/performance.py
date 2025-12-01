"""Performance optimization utilities for network simulator integration.

This module provides performance enhancements including:
- Response caching with TTL
- Request batching/pooling
- Rate limiting
- Connection pooling

Classes:
    ResponseCache: TTL-based response cache
    RequestBatcher: Batch multiple requests together
    RateLimiter: Token bucket rate limiter
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Generic, Optional, TypeVar
from collections import OrderedDict

log = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Response Caching
# =============================================================================


@dataclass
class CacheEntry(Generic[T]):
    """Entry in the response cache."""

    value: T
    created_at: float
    ttl: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > (self.created_at + self.ttl)

    @property
    def age(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at


@dataclass
class CacheStats:
    """Statistics for cache performance."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    entries: int = 0
    memory_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class ResponseCache(Generic[T]):
    """TTL-based response cache with LRU eviction.

    Provides caching for expensive operations with automatic TTL-based
    expiration and LRU eviction when capacity is reached.

    Features:
        - TTL-based expiration
        - LRU eviction when full
        - Statistics tracking
        - Key hashing for complex objects
        - Optional stale-while-revalidate

    Attributes:
        default_ttl: Default TTL for entries (seconds).
        max_size: Maximum number of entries.

    Example:
        >>> cache = ResponseCache[dict](default_ttl=60, max_size=1000)
        >>> cache.set("key", {"data": "value"})
        >>> result = cache.get("key")
        >>> print(f"Hit rate: {cache.stats.hit_rate:.2%}")
    """

    def __init__(
        self,
        default_ttl: float = 60.0,
        max_size: int = 1000,
        stale_ttl: float = 0.0,
    ) -> None:
        """Initialize response cache.

        Args:
            default_ttl: Default TTL for entries in seconds.
            max_size: Maximum number of entries.
            stale_ttl: Additional TTL for stale-while-revalidate (0 = disabled).
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.stale_ttl = stale_ttl
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._stats = CacheStats()
        self._lock = asyncio.Lock()

    @property
    def stats(self) -> CacheStats:
        """Get cache statistics."""
        self._stats.entries = len(self._cache)
        return self._stats

    def _make_key(self, key: Any) -> str:
        """Create cache key from any object.

        Args:
            key: The key object (can be string, dict, etc.).

        Returns:
            String key for cache storage.
        """
        if isinstance(key, str):
            return key
        # Hash complex objects
        try:
            key_str = json.dumps(key, sort_keys=True)
            return hashlib.md5(key_str.encode()).hexdigest()
        except (TypeError, ValueError):
            return str(hash(str(key)))

    def get(self, key: Any) -> Optional[T]:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found/expired.
        """
        cache_key = self._make_key(key)

        if cache_key not in self._cache:
            self._stats.misses += 1
            return None

        entry = self._cache[cache_key]

        if entry.is_expired:
            # Check stale-while-revalidate
            if self.stale_ttl > 0:
                stale_expires = entry.created_at + entry.ttl + self.stale_ttl
                if time.time() <= stale_expires:
                    # Return stale value
                    entry.hits += 1
                    self._stats.hits += 1
                    log.debug(f"Cache stale hit: {cache_key}")
                    return entry.value

            # Expired and not stale-eligible
            del self._cache[cache_key]
            self._stats.misses += 1
            self._stats.evictions += 1
            return None

        # Move to end for LRU
        self._cache.move_to_end(cache_key)
        entry.hits += 1
        self._stats.hits += 1
        log.debug(f"Cache hit: {cache_key}")
        return entry.value

    def set(self, key: Any, value: T, ttl: Optional[float] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Optional TTL override (uses default if not specified).
        """
        cache_key = self._make_key(key)

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats.evictions += 1
            log.debug(f"Cache eviction (LRU): {oldest_key}")

        # Add new entry
        self._cache[cache_key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl if ttl is not None else self.default_ttl,
        )
        log.debug(f"Cache set: {cache_key}")

    def invalidate(self, key: Any) -> bool:
        """Invalidate a specific cache entry.

        Args:
            key: Cache key.

        Returns:
            True if entry was invalidated, False if not found.
        """
        cache_key = self._make_key(key)
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._stats.evictions += 1
            log.debug(f"Cache invalidate: {cache_key}")
            return True
        return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all entries matching a pattern.

        Args:
            pattern: Key pattern to match (simple substring match).

        Returns:
            Number of entries invalidated.
        """
        keys_to_delete = [k for k in self._cache if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]
            self._stats.evictions += 1
        log.debug(f"Cache invalidate pattern '{pattern}': {len(keys_to_delete)} entries")
        return len(keys_to_delete)

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats.evictions += count
        log.debug(f"Cache cleared: {count} entries")

    async def get_or_set(
        self,
        key: Any,
        factory: Callable[[], Coroutine[Any, Any, T]],
        ttl: Optional[float] = None,
    ) -> T:
        """Get from cache or compute and cache value.

        Args:
            key: Cache key.
            factory: Async function to compute value if not cached.
            ttl: Optional TTL override.

        Returns:
            Cached or newly computed value.
        """
        async with self._lock:
            # Check cache first
            value = self.get(key)
            if value is not None:
                return value

            # Compute and cache
            value = await factory()
            self.set(key, value, ttl)
            return value


# =============================================================================
# Request Batching
# =============================================================================


@dataclass
class BatchedRequest:
    """A request waiting in the batch queue."""

    request_id: str
    method: str
    params: dict[str, Any]
    future: asyncio.Future
    created_at: float = field(default_factory=time.time)


@dataclass
class BatchConfig:
    """Configuration for request batching.

    Attributes:
        max_batch_size: Maximum requests per batch.
        max_wait_time: Maximum wait time before sending batch (seconds).
        enabled_methods: Methods eligible for batching (None = all).
    """

    max_batch_size: int = 10
    max_wait_time: float = 0.05  # 50ms
    enabled_methods: Optional[set[str]] = None


class RequestBatcher:
    """Batch multiple requests together for efficiency.

    Collects requests and sends them in batches to reduce
    round-trip overhead. Useful for high-frequency operations.

    Features:
        - Time-based and size-based batch triggers
        - Per-method batching configuration
        - Automatic batch assembly
        - Result distribution to individual requests

    Example:
        >>> batcher = RequestBatcher(send_batch_func)
        >>> result = await batcher.add_request("ue.list", {})
    """

    def __init__(
        self,
        batch_sender: Callable[
            [list[dict[str, Any]]], Coroutine[Any, Any, list[dict[str, Any]]]
        ],
        config: Optional[BatchConfig] = None,
    ) -> None:
        """Initialize request batcher.

        Args:
            batch_sender: Async function to send batch of requests.
            config: Batching configuration.
        """
        self._batch_sender = batch_sender
        self._config = config or BatchConfig()
        self._queue: list[BatchedRequest] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def config(self) -> BatchConfig:
        """Get batching configuration."""
        return self._config

    def is_batchable(self, method: str) -> bool:
        """Check if a method is eligible for batching.

        Args:
            method: Method name.

        Returns:
            True if method can be batched.
        """
        if self._config.enabled_methods is None:
            return True
        return method in self._config.enabled_methods

    async def add_request(
        self,
        request_id: str,
        method: str,
        params: dict[str, Any],
    ) -> Any:
        """Add a request to the batch queue.

        Args:
            request_id: Unique request identifier.
            method: Method name.
            params: Request parameters.

        Returns:
            Result from the batch response.
        """
        future: asyncio.Future = asyncio.get_event_loop().create_future()

        request = BatchedRequest(
            request_id=request_id,
            method=method,
            params=params,
            future=future,
        )

        async with self._lock:
            self._queue.append(request)

            # Check if we should flush immediately
            if len(self._queue) >= self._config.max_batch_size:
                await self._flush()
            elif self._flush_task is None:
                # Schedule flush after max_wait_time
                self._flush_task = asyncio.create_task(
                    self._delayed_flush(self._config.max_wait_time)
                )

        # Wait for result
        return await future

    async def _delayed_flush(self, delay: float) -> None:
        """Flush after a delay."""
        await asyncio.sleep(delay)
        async with self._lock:
            if self._queue:
                await self._flush()
            self._flush_task = None

    async def _flush(self) -> None:
        """Flush the current batch."""
        if not self._queue:
            return

        # Take all queued requests
        batch = self._queue[:]
        self._queue.clear()

        log.debug(f"Flushing batch of {len(batch)} requests")

        # Build batch request
        requests = [
            {
                "jsonrpc": "2.0",
                "method": req.method,
                "params": req.params,
                "id": req.request_id,
            }
            for req in batch
        ]

        try:
            # Send batch
            responses = await self._batch_sender(requests)

            # Map responses to requests
            response_map = {resp.get("id"): resp for resp in responses}

            for req in batch:
                resp = response_map.get(req.request_id)
                if resp is None:
                    req.future.set_exception(
                        Exception(f"No response for request {req.request_id}")
                    )
                elif "error" in resp:
                    req.future.set_exception(
                        Exception(resp["error"].get("message", "Unknown error"))
                    )
                else:
                    req.future.set_result(resp.get("result"))

        except Exception as e:
            # Fail all requests in batch
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(e)

    async def flush_pending(self) -> None:
        """Flush any pending requests immediately."""
        async with self._lock:
            if self._flush_task:
                self._flush_task.cancel()
                self._flush_task = None
            await self._flush()


# =============================================================================
# Rate Limiting
# =============================================================================


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter.

    Attributes:
        rate: Maximum requests per second.
        burst: Maximum burst size (bucket capacity).
    """

    rate: float = 10.0
    burst: int = 20


class RateLimiter:
    """Token bucket rate limiter.

    Controls the rate of operations using the token bucket algorithm.
    Allows bursts up to a configured limit while maintaining an
    average rate.

    Attributes:
        config: Rate limiter configuration.

    Example:
        >>> limiter = RateLimiter(RateLimiterConfig(rate=10, burst=20))
        >>> async with limiter:
        ...     await make_request()
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None) -> None:
        """Initialize rate limiter.

        Args:
            config: Rate limiter configuration.
        """
        self.config = config or RateLimiterConfig()
        self._tokens = float(self.config.burst)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            self.config.burst,
            self._tokens + elapsed * self.config.rate,
        )
        self._last_update = now

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            Time waited in seconds.
        """
        async with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return 0.0

            # Calculate wait time
            needed = tokens - self._tokens
            wait_time = needed / self.config.rate

            await asyncio.sleep(wait_time)

            self._refill()
            self._tokens -= tokens
            return wait_time

    async def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens acquired, False otherwise.
        """
        async with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    @property
    def available_tokens(self) -> float:
        """Get number of available tokens."""
        self._refill()
        return self._tokens

    async def __aenter__(self) -> "RateLimiter":
        """Acquire one token on context entry."""
        await self.acquire(1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context exit (no action needed)."""
        pass


# =============================================================================
# Cached Manager Decorator
# =============================================================================


def cached_method(
    ttl: float = 60.0,
    key_func: Optional[Callable[..., str]] = None,
    cache_attr: str = "_cache",
) -> Callable:
    """Decorator for caching async method results.

    Args:
        ttl: Cache TTL in seconds.
        key_func: Function to generate cache key from method args.
        cache_attr: Attribute name for cache on instance.

    Returns:
        Decorated method.

    Example:
        >>> class MyManager:
        ...     _cache = ResponseCache()
        ...
        ...     @cached_method(ttl=30)
        ...     async def get_data(self, id: str):
        ...         return await self._fetch_data(id)
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(self, *args, **kwargs) -> Any:
            # Get or create cache on instance
            cache: ResponseCache = getattr(self, cache_attr, None)
            if cache is None:
                cache = ResponseCache(default_ttl=ttl)
                setattr(self, cache_attr, cache)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"

            # Try cache first
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Call function and cache result
            result = await func(self, *args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
