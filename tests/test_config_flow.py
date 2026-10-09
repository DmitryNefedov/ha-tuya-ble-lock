import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ble_lock.api import TuyaAuthError, TuyaConnectionError
from custom_components.tuya_ble_lock.const import DOMAIN

USER_INPUT = {"client_id": "abc123", "client_secret": "s", "region": "eu-west"}


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_success(hass, api):
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == USER_INPUT
    api.authenticate.assert_awaited_once()


@pytest.mark.parametrize(
    ("exc", "error"),
    [(TuyaAuthError("bad"), "invalid_auth"), (TuyaConnectionError("down"), "cannot_connect")],
)
async def test_errors_then_recovery(hass, api, exc, error):
    api.authenticate.side_effect = exc
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    api.authenticate.side_effect = None
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_entry(hass, api):
    MockConfigEntry(domain=DOMAIN, unique_id="abc123", data=USER_INPUT).add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_sets_poll_interval(hass, api, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"poll_interval": 120}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"poll_interval": 120}
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 120
