"""
Global throughput shaping using token bucket algorithm for better concurrency.

Shared across all download segments via one limiter instance.
"""

from __future__ import annotations

import asyncio
import time


class SpeedLimiter:
    """
    Token bucket rate limiter for better concurrency.
    
    Uses a token bucket algorithm where tokens are added at a constant rate.
    consume(n) waits until enough tokens are available.
    max_bps <= 0 means unlimited.
    """

    __slots__ = ("max_bps", "_tokens", "_last_update", "_lock", "_bucket_capacity")

    def __init__(self, max_bps: float = 0.0):
        self.max_bps = max(0.0, float(max_bps))
        self._tokens = 0.0
        self._last_update = time.time()
        self._lock = asyncio.Lock()
        # Bucket capacity allows for short bursts (1 second worth of tokens)
        self._bucket_capacity = max_bps if max_bps > 0 else 0

    def set_limit_bps(self, bps: float) -> None:
        """Update the rate limit and bucket capacity."""
        self.max_bps = max(0.0, float(bps))
        self._bucket_capacity = self.max_bps
        # Note: tokens will be clamped to new capacity on next consume() call

    async def consume(self, nbytes: int) -> None:
        """
        Consume nbytes from the token bucket.
        
        Waits until enough tokens are available.
        """
        if nbytes <= 0:
            return
        limit = self.max_bps
        if limit <= 0:
            return
        
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_update
            
            # Add tokens based on elapsed time
            if elapsed > 0:
                self._tokens = min(
                    self._bucket_capacity,
                    self._tokens + elapsed * limit
                )
                self._last_update = now
            
            # If not enough tokens, wait for them
            if self._tokens < nbytes:
                needed = nbytes - self._tokens
                wait_time = needed / limit
                await asyncio.sleep(wait_time)
                
                # Recalculate after sleep
                now = time.time()
                elapsed = now - self._last_update
                self._tokens = min(
                    self._bucket_capacity,
                    self._tokens + elapsed * limit
                )
                self._last_update = now
            
            # Consume tokens
            self._tokens -= nbytes
