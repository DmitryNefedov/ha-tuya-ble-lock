from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DP_BATTERY
from .coordinator import TuyaLockConfigEntry
from .entity import TuyaLockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TuyaLockConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TuyaLockBattery(coordinator, device_id)
        for device_id in coordinator.locks
        if DP_BATTERY in coordinator.data[device_id]
    )


class TuyaLockBattery(TuyaLockEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _unique_id_suffix = "_battery"

    @property
    def native_value(self) -> int | None:
        return self._status.get(DP_BATTERY)
