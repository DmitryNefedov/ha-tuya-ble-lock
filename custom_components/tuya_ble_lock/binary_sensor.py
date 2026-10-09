from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TuyaLockConfigEntry, TuyaLockCoordinator
from .entity import TuyaLockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaLockConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[TuyaLockEntity] = []
    for id_ in coordinator.locks:
        status = coordinator.data.get(id_, {})
        if "closed_opened" in status:
            entities.append(TuyaLockDoor(coordinator, id_))
        if "reverse_lock" in status:
            entities.append(TuyaLockDoubleLocked(coordinator, id_))
    async_add_entities(entities)


class TuyaLockDoor(TuyaLockEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: TuyaLockCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_door"

    @property
    def is_on(self) -> bool | None:
        # Value mapping is unconfirmed until a live status dump.
        value = self._status.get("closed_opened")
        if isinstance(value, bool):
            return value
        return {"open": True, "closed": False}.get(value)


class TuyaLockDoubleLocked(TuyaLockEntity, BinarySensorEntity):
    _attr_translation_key = "double_locked"

    def __init__(self, coordinator: TuyaLockCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_double_locked"

    @property
    def is_on(self) -> bool | None:
        value = self._status.get("reverse_lock")
        return value if isinstance(value, bool) else None
