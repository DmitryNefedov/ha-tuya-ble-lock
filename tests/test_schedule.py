from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.tuya_ble_lock.schedule import next_poll_delay

TZ = ZoneInfo("Australia/Sydney")


def at(hour, minute=0, second=0):
    return datetime(2026, 10, 9, hour, minute, second, tzinfo=TZ)


@pytest.mark.parametrize(
    ("now", "seconds"),
    [
        (at(7, 30), 60),
        (at(8), 60),
        (at(9, 59, 30), 30),  # the next poll lands on the window edge
        (at(10), 1800),
        (at(12), 1800),
        (at(14, 45), 900),
        (at(15), 60),
        (at(18, 29, 30), 30),
        (at(18, 30), 1800),
        (at(23), 1800),
        (at(3), 1800),
        (at(7, 15), 900),
    ],
)
def test_next_poll_delay(now, seconds):
    assert next_poll_delay(now) == timedelta(seconds=seconds)


def test_polls_per_day_stay_within_the_tuya_trial_budget():
    start = at(7, 30)
    now, polls = start, 0
    while now < start + timedelta(days=1):
        polls += 1
        now += next_poll_delay(now)
    assert polls == 396  # 11,880 a month; Tuya's trial allows 26,000 calls a month in total
