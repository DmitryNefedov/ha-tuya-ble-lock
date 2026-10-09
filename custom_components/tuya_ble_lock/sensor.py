from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
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
    async_add_entities(
        TuyaLockBattery(coordinator, id_)
        for id_ in coordinator.locks
        if "residual_electricity" in coordinator.data.get(id_, {})
    )


class TuyaLockBattery(TuyaLockEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: TuyaLockCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_battery"

    @property
    def native_value(self) -> int | None:
        return self._status.get("residual_electricity")
