from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TuyaError, TuyaLockApi
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type TuyaLockConfigEntry = ConfigEntry[TuyaLockCoordinator]


class TuyaLockCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls the status of every Lock. The data is {device_id: {data point code: value}}."""

    config_entry: TuyaLockConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TuyaLockConfigEntry, api: TuyaLockApi
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            ),
        )
        self.api = api
        self.locks: dict[str, dict[str, Any]] = {}
        self.last_unlocks: dict[str, dict[str, Any] | None] = {}

    async def async_load_locks(self) -> None:
        """Fetch the device list. Done once at setup, not on every poll."""
        try:
            self.locks = {d["id"]: d for d in await self.api.list_locks()}
        except TuyaError as err:
            raise ConfigEntryNotReady(f"Could not list Locks: {err}") from err

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            data = {id_: await self.api.get_status(id_) for id_ in self.locks}
        except TuyaError as err:
            raise UpdateFailed(f"Error talking to Tuya Cloud: {err}") from err
        for id_ in self.locks:
            try:
                self.last_unlocks[id_] = await self.api.last_unlock(id_)
            except TuyaError as err:
                _LOGGER.debug("Could not read the unlock history of %s: %s", id_, err)
        return data
