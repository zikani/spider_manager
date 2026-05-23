import asyncio
import time

from core.speed_limiter import SpeedLimiter


def test_unlimited_skips_sleep():
    lim = SpeedLimiter(0)

    async def _run():
        t0 = time.perf_counter()
        await lim.consume(1_000_000)
        assert time.perf_counter() - t0 < 0.05

    asyncio.run(_run())


def test_cap_adds_delay():
    lim = SpeedLimiter(100_000)

    async def _run():
        t0 = time.perf_counter()
        await lim.consume(100_000)
        dt = time.perf_counter() - t0
        assert dt >= 0.85

    asyncio.run(_run())
