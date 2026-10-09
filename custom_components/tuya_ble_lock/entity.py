from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TuyaLockCoordinator


class TuyaLockEntity(CoordinatorEntity[TuyaLockCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TuyaLockCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        info = coordinator.locks[device_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=info.get("name", device_id),
            manufacturer="Tuya",
            model=info.get("product_name"),
            model_id=info.get("product_id"),
        )

    @property
    def _status(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._device_id, {})
