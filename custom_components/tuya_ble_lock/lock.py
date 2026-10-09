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

# The Lock unlocks about 10 s after a command and re-locks about 6 s later, so the
# state is followed for 30 s instead of waiting for the next regular poll.
REFRESH_EVERY = 5
REFRESH_COUNT = 6


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
        self._schedule_refresh(REFRESH_COUNT)

    def _schedule_refresh(self, remaining: int) -> None:
        if self._cancel_refresh:
            self._cancel_refresh()
        self._cancel_refresh = async_call_later(
            self.hass, REFRESH_EVERY, partial(self._refresh_after_command, remaining)
        )

    async def _refresh_after_command(self, remaining: int, _now: Any) -> None:
        self._cancel_refresh = None
        await self.coordinator.async_refresh()
        if remaining > 1:
            self._schedule_refresh(remaining - 1)

    async def async_will_remove_from_hass(self) -> None:
        if self._cancel_refresh:
            self._cancel_refresh()
