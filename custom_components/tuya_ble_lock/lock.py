from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .api import TuyaError, is_locked
from .coordinator import TuyaLockConfigEntry
from .entity import TuyaLockEntity

# The Lock reports its new state a few seconds after the Gateway relays the command.
REFRESH_DELAY = 5


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
        if self._cancel_refresh:
            self._cancel_refresh()
        self._cancel_refresh = async_call_later(
            self.hass, REFRESH_DELAY, self._refresh_after_command
        )

    async def _refresh_after_command(self, _now: Any) -> None:
        self._cancel_refresh = None
        await self.coordinator.async_request_refresh()

    async def async_will_remove_from_hass(self) -> None:
        if self._cancel_refresh:
            self._cancel_refresh()
