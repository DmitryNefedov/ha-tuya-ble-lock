from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DP_DOOR, DP_DOUBLE_LOCK
from .coordinator import TuyaLockConfigEntry
from .entity import TuyaLockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaLockConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[TuyaLockEntity] = []
    for device_id in coordinator.locks:
        status = coordinator.data[device_id]
        if DP_DOOR in status:
            entities.append(TuyaLockDoor(coordinator, device_id))
        if DP_DOUBLE_LOCK in status:
            entities.append(TuyaLockDoubleLocked(coordinator, device_id))
    async_add_entities(entities)


class TuyaLockDoor(TuyaLockEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _unique_id_suffix = "_door"

    @property
    def is_on(self) -> bool | None:
        # Only "unknown" has been seen so far; open/closed are assumed.
        value = self._status.get(DP_DOOR)
        if isinstance(value, bool):
            return value
        return {"open": True, "closed": False}.get(value)


class TuyaLockDoubleLocked(TuyaLockEntity, BinarySensorEntity):
    _attr_translation_key = "double_locked"
    _unique_id_suffix = "_double_locked"

    @property
    def is_on(self) -> bool | None:
        value = self._status.get(DP_DOUBLE_LOCK)
        return value if isinstance(value, bool) else None
