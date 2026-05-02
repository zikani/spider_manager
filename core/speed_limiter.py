"""
Global throughput shaping: sleep proportional to bytes so aggregate rate stays near the cap.

Shared across all download segments via one limiter instance.
"""

from __future__ import annotations

import asyncio


class SpeedLimiter:
    """
    Simple async throttle: each `consume(n)` sleeps n/max_bps seconds (steady rate).
    max_bps <= 0 means unlimited.
    """

    __slots__ = ("max_bps", "_lock")

    def __init__(self, max_bps: float = 0.0):
        self.max_bps = max(0.0, float(max_bps))
        self._lock = asyncio.Lock()

    def set_limit_bps(self, bps: float) -> None:
        self.max_bps = max(0.0, float(bps))

    async def consume(self, nbytes: int) -> None:
        if nbytes <= 0:
            return
        limit = self.max_bps
        if limit <= 0:
            return
        delay = nbytes / limit
        if delay <= 0:
            return
        async with self._lock:
            await asyncio.sleep(delay)
