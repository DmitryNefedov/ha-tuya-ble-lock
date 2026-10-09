"""Poll schedule, sized for Tuya's free trial of 26,000 API calls a month."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

BUSY_WINDOWS = ((time(7, 30), time(10, 0)), (time(15, 0), time(18, 30)))
BUSY_EVERY = timedelta(minutes=1)
QUIET_EVERY = timedelta(minutes=30)


def next_poll_delay(now: datetime) -> timedelta:
    """Time until the next poll. `now` must be in Home Assistant's timezone."""
    busy = any(start <= now.time() < end for start, end in BUSY_WINDOWS)
    edges = [
        datetime.combine(now.date() + timedelta(days=days), edge, tzinfo=now.tzinfo)
        for days in (0, 1)
        for window in BUSY_WINDOWS
        for edge in window
    ]
    next_edge = min(edge for edge in edges if edge > now)
    until_edge = next_edge.astimezone(UTC) - now.astimezone(UTC)
    return min(BUSY_EVERY if busy else QUIET_EVERY, until_edge)
