from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

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
    async_add_entities(TuyaLockLastUnlock(coordinator, device_id) for device_id in coordinator.locks)


class TuyaLockBattery(TuyaLockEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _unique_id_suffix = "_battery"

    @property
    def native_value(self) -> int | None:
        return self._status.get(DP_BATTERY)


class TuyaLockLastUnlock(TuyaLockEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_unlock"
    _unique_id_suffix = "_last_unlock"

    @property
    def _last_unlock(self) -> dict[str, Any] | None:
        return self.coordinator.last_unlocks.get(self._device_id)

    @property
    def native_value(self) -> datetime | None:
        if not self._last_unlock:
            return None
        return datetime.fromtimestamp(self._last_unlock["time"] / 1000, UTC)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self._last_unlock:
            return None
        return {key: self._last_unlock[key] for key in ("method", "name", "user")}
