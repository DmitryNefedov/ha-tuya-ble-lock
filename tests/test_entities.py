from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.tuya_ble_lock.api import TuyaApiError, TuyaConnectionError
from custom_components.tuya_ble_lock.const import DOMAIN

from .conftest import LAST_UNLOCK, LOCK_ID, STATUS_LOCKED

LOCK = "lock.front_door"
BATTERY = "sensor.front_door_battery"
DOOR = "binary_sensor.front_door_door"
DOUBLE = "binary_sensor.front_door_double_locked"
LAST_UNLOCK_SENSOR = "sensor.front_door_last_unlock"


async def _at(hass, freezer, hour, minute=0, tz="Australia/Sydney"):
    """Set Home Assistant's timezone and the (frozen) local time of day."""
    await hass.config.async_set_time_zone(tz)
    freezer.move_to(datetime(2026, 10, 9, hour, minute, tzinfo=ZoneInfo(tz)))


async def _setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities_from_status(hass, api, entry):
    await _setup(hass, entry)
    assert hass.states.get(LOCK).state == "locked"
    assert hass.states.get(BATTERY).state == "87"
    assert hass.states.get(DOOR).state == STATE_OFF
    assert hass.states.get(DOUBLE).state == STATE_OFF


async def test_unique_ids(hass, api, entry):
    await _setup(hass, entry)
    registry = er.async_get(hass)
    assert registry.async_get(LOCK).unique_id == LOCK_ID
    assert registry.async_get(BATTERY).unique_id == f"{LOCK_ID}_battery"
    assert registry.async_get(DOOR).unique_id == f"{LOCK_ID}_door"
    assert registry.async_get(DOUBLE).unique_id == f"{LOCK_ID}_double_locked"


async def test_device_registry(hass, api, entry):
    await _setup(hass, entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, LOCK_ID)})
    assert device.name == "Front door"
    assert device.model == "WUN-AXDL-261"


async def test_unlocked_and_door_open(hass, api, entry):
    api.get_status.return_value = {**STATUS_LOCKED, "lock_motor_state": True, "closed_opened": "open"}
    await _setup(hass, entry)
    assert hass.states.get(LOCK).state == "unlocked"
    assert hass.states.get(DOOR).state == STATE_ON


async def test_missing_data_points_not_created_and_lock_unknown(hass, api, entry):
    api.get_status.return_value = {}
    await _setup(hass, entry)
    assert hass.states.get(LOCK).state == STATE_UNKNOWN
    assert hass.states.get(BATTERY) is None
    assert hass.states.get(DOOR) is None
    assert hass.states.get(DOUBLE) is None


async def test_no_locks_creates_no_entities(hass, api, entry):
    api.list_locks.return_value = []
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.async_entity_ids() == []


@pytest.mark.parametrize(("service", "open_"), [("unlock", True), ("lock", False)])
async def test_lock_services_call_operate(hass, api, entry, service, open_):
    await _setup(hass, entry)
    api.get_status.reset_mock()
    await hass.services.async_call("lock", service, {"entity_id": LOCK}, blocking=True)
    api.operate.assert_awaited_once_with(LOCK_ID, open_)
    api.get_status.assert_not_awaited()  # the Lock needs a few seconds to report


async def test_state_is_followed_after_a_command(hass, freezer, api, entry):
    """The Lock unlocks about 10 s after the command and re-locks about 6 s later."""
    await _at(hass, freezer, 12)  # quiet hours: no regular poll interferes
    await _setup(hass, entry)
    api.get_status.reset_mock()
    api.last_unlock.reset_mock()
    await hass.services.async_call("lock", "unlock", {"entity_id": LOCK}, blocking=True)

    api.get_status.return_value = {**STATUS_LOCKED, "lock_motor_state": True}
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=13))
    await hass.async_block_till_done()
    assert hass.states.get(LOCK).state == "unlocked"
    api.last_unlock.assert_not_awaited()

    api.get_status.return_value = {**STATUS_LOCKED, "lock_motor_state": False}
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=22))
    await hass.async_block_till_done()
    assert hass.states.get(LOCK).state == "locked"
    assert api.get_status.await_count == 2
    assert api.last_unlock.await_count == 1  # the unlock history is read once, at the end

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=60))
    await hass.async_block_till_done()
    assert api.get_status.await_count == 2  # then back to the normal schedule


@pytest.mark.parametrize(
    ("hour", "minute", "tz", "interval"),
    [
        (8, 0, "Australia/Sydney", timedelta(minutes=1)),
        (12, 0, "Australia/Sydney", timedelta(minutes=30)),
        (16, 0, "Australia/Sydney", timedelta(minutes=1)),
        (21, 0, "Australia/Sydney", timedelta(minutes=30)),
        (21, 0, "UTC", timedelta(minutes=30)),
        (8, 0, "UTC", timedelta(minutes=1)),
    ],
)
async def test_poll_interval_follows_local_time_of_day(hass, freezer, api, entry, hour, minute, tz, interval):
    await _at(hass, freezer, hour, minute, tz)
    await _setup(hass, entry)
    assert entry.runtime_data.update_interval == interval


async def test_unlock_history_is_not_read_on_every_poll(hass, freezer, api, entry):
    await _at(hass, freezer, 8)
    await _setup(hass, entry)
    await entry.runtime_data.async_refresh()
    assert api.last_unlock.await_count == 1
    freezer.tick(timedelta(minutes=31))
    await entry.runtime_data.async_refresh()
    assert api.last_unlock.await_count == 2


async def test_last_unlock_sensor(hass, api, entry):
    await _setup(hass, entry)
    state = hass.states.get(LAST_UNLOCK_SENSOR)
    assert state.state == datetime.fromtimestamp(LAST_UNLOCK["time"] // 1000, UTC).isoformat()
    assert state.attributes["method"] == LAST_UNLOCK["method"]
    assert state.attributes["name"] == "Left Thumb"
    assert er.async_get(hass).async_get(LAST_UNLOCK_SENSOR).unique_id == f"{LOCK_ID}_last_unlock"


async def test_last_unlock_sensor_unknown_without_entries(hass, api, entry):
    api.last_unlock.return_value = None
    await _setup(hass, entry)
    assert hass.states.get(LAST_UNLOCK_SENSOR).state == STATE_UNKNOWN


async def test_last_unlock_failure_does_not_break_the_lock(hass, api, entry):
    api.last_unlock.side_effect = TuyaApiError(1108, "uri path invalid")
    await _setup(hass, entry)
    assert hass.states.get(LOCK).state == "locked"
    assert hass.states.get(LAST_UNLOCK_SENSOR).state == STATE_UNKNOWN


async def test_rejected_command_raises(hass, api, entry):
    await _setup(hass, entry)
    api.operate.side_effect = TuyaApiError(2008, "remote unlock disabled")
    with pytest.raises(HomeAssistantError, match="remote unlock disabled"):
        await hass.services.async_call("lock", "unlock", {"entity_id": LOCK}, blocking=True)


async def test_setup_retries_when_device_list_fails(hass, api, entry):
    api.list_locks.side_effect = TuyaConnectionError("down")
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_poll_failure_makes_entities_unavailable(hass, freezer, api, entry):
    await _at(hass, freezer, 8)
    await _setup(hass, entry)
    api.get_status.side_effect = TuyaConnectionError("down")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()
    assert hass.states.get(LOCK).state == STATE_UNAVAILABLE


async def test_unload(hass, api, entry):
    await _setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
