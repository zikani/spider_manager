from datetime import datetime

from core.scheduler import downloads_allowed_now


def test_scheduler_disabled_always_allows():
    assert downloads_allowed_now(
        enabled=False,
        start_hhmm="09:00",
        end_hhmm="17:00",
        now=datetime(2026, 5, 2, 12, 0),
    )


def test_same_day_window_inside():
    assert downloads_allowed_now(
        enabled=True,
        start_hhmm="09:00",
        end_hhmm="17:00",
        now=datetime(2026, 5, 2, 12, 0),
    )
    assert not downloads_allowed_now(
        enabled=True,
        start_hhmm="09:00",
        end_hhmm="17:00",
        now=datetime(2026, 5, 2, 18, 0),
    )


def test_overnight_window():
    assert downloads_allowed_now(
        enabled=True,
        start_hhmm="22:00",
        end_hhmm="06:00",
        now=datetime(2026, 5, 2, 23, 30),
    )
    assert downloads_allowed_now(
        enabled=True,
        start_hhmm="22:00",
        end_hhmm="06:00",
        now=datetime(2026, 5, 2, 5, 15),
    )
    assert not downloads_allowed_now(
        enabled=True,
        start_hhmm="22:00",
        end_hhmm="06:00",
        now=datetime(2026, 5, 2, 14, 0),
    )


def test_window_boundaries_touch():
    assert downloads_allowed_now(
        enabled=True,
        start_hhmm="09:00",
        end_hhmm="17:00",
        now=datetime(2026, 5, 2, 9, 0),
    )
    assert downloads_allowed_now(
        enabled=True,
        start_hhmm="09:00",
        end_hhmm="17:00",
        now=datetime(2026, 5, 2, 17, 0),
    )

