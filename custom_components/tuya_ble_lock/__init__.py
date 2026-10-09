from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TuyaLockApi
from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_REGION
from .coordinator import TuyaLockConfigEntry, TuyaLockCoordinator

PLATFORMS = [Platform.LOCK, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: TuyaLockConfigEntry) -> bool:
    api = TuyaLockApi(
        async_get_clientsession(hass),
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
        entry.data[CONF_REGION],
    )
    coordinator = TuyaLockCoordinator(hass, entry, api)
    await coordinator.async_load_locks()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TuyaLockConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
