"""
Time-window gating for starting new downloads (local clock).
Supports ranges that wrap past midnight (e.g. 22:00 → 06:00).
"""

from __future__ import annotations

from datetime import datetime


def _parse_hhmm(s: str) -> tuple[int, int]:
    s = (s or "00:00").strip()
    parts = s.replace(".", ":").split(":")
    h = max(0, min(23, int(parts[0])))
    m = max(0, min(59, int(parts[1]) if len(parts) > 1 else 0))
    return h, m


def _minutes_since_midnight(h: int, m: int) -> int:
    return h * 60 + m


def downloads_allowed_now(
    *,
    enabled: bool,
    start_hhmm: str,
    end_hhmm: str,
    now: datetime | None = None,
) -> bool:
    """
    Returns True when new downloads may be dispatched.
    """
    if not enabled:
        return True
    dt = now or datetime.now()
    cur = dt.hour * 60 + dt.minute
    sh, sm = _parse_hhmm(start_hhmm)
    eh, em = _parse_hhmm(end_hhmm)
    start_m = _minutes_since_midnight(sh, sm)
    end_m = _minutes_since_midnight(eh, em)
    if start_m <= end_m:
        return start_m <= cur <= end_m
    return cur >= start_m or cur <= end_m
