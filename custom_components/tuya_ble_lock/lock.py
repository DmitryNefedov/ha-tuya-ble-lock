from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import TuyaError
from .coordinator import TuyaLockConfigEntry, TuyaLockCoordinator
from .entity import TuyaLockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaLockConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(TuyaLock(coordinator, id_) for id_ in coordinator.locks)


class TuyaLock(TuyaLockEntity, LockEntity):
    _attr_name = None

    def __init__(self, coordinator: TuyaLockCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id

    @property
    def is_locked(self) -> bool | None:
        # lock_motor_state is True while the bolt is retracted. Unconfirmed until a live status dump.
        motor = self._status.get("lock_motor_state")
        return None if not isinstance(motor, bool) else not motor

    async def async_lock(self, **kwargs: Any) -> None:
        await self._operate(False)

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._operate(True)

    async def _operate(self, open_: bool) -> None:
        try:
            await self.coordinator.api.operate(self._device_id, open_)
        except TuyaError as err:
            raise HomeAssistantError(
                f"Could not {'unlock' if open_ else 'lock'} {self.device_info['name']}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
