from __future__ import annotations

from functools import partial
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .api import TuyaError, is_locked
from .coordinator import TuyaLockConfigEntry
from .entity import TuyaLockEntity

# The Lock unlocks about 10 s after a command and re-locks about 6 s later, so after a
# command the state is read every 5 s, at most 6 times (not left to the next poll). The
# reads stop early once the lock has unlocked and locked again. Each read costs an API call.
FOLLOW_UP_EVERY = 5
FOLLOW_UP_CHECKS = 6


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaLockConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(TuyaLock(coordinator, device_id) for device_id in coordinator.locks)


class TuyaLock(TuyaLockEntity, LockEntity):
    _attr_name = None
    _cancel_refresh: CALLBACK_TYPE | None = None
    _command_unlocks = False
    _seen_unlocked = False

    @property
    def is_locked(self) -> bool | None:
        return is_locked(self._status)

    async def async_lock(self, **kwargs: Any) -> None:
        await self._operate(unlock=False)

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._operate(unlock=True)

    async def _operate(self, *, unlock: bool) -> None:
        try:
            await self.coordinator.api.operate(self._device_id, unlock)
        except TuyaError as err:
            raise HomeAssistantError(
                f"Could not {'unlock' if unlock else 'lock'} {self._name}: {err}"
            ) from err
        # Without a state change the more-info toggle stays where the user flipped it,
        # and the Lock often goes unlocked and back between two reads.
        self._command_unlocks = unlock
        self._seen_unlocked = False
        self._attr_is_unlocking = unlock
        self._attr_is_locking = not unlock
        self.async_write_ha_state()
        self._schedule_follow_up(FOLLOW_UP_CHECKS)

    def _schedule_follow_up(self, checks_left: int) -> None:
        if self._cancel_refresh:
            self._cancel_refresh()
        self._cancel_refresh = async_call_later(
            self.hass, FOLLOW_UP_EVERY, partial(self._follow_up, checks_left)
        )

    async def _follow_up(self, checks_left: int, _now: Any) -> None:
        self._cancel_refresh = None
        await self.coordinator.async_refresh()
        locked = self.is_locked
        checks_left -= 1
        if self._command_unlocks:
            self._seen_unlocked = self._seen_unlocked or locked is False
            settled = self._seen_unlocked
            done = self._seen_unlocked and locked is True
        else:
            settled = done = locked is True
        if settled or not checks_left:
            self._attr_is_unlocking = self._attr_is_locking = False
            self.async_write_ha_state()
        if done or not checks_left:
            await self.coordinator.async_read_unlock_history()
        else:
            self._schedule_follow_up(checks_left)

    async def async_will_remove_from_hass(self) -> None:
        if self._cancel_refresh:
            self._cancel_refresh()
