from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ble_lock.const import DOMAIN

LOCK_ID = "bf464bxgmiecskga"

LOCK_INFO = {
    "id": LOCK_ID,
    "name": "Front door",
    "category": "jtmspro",
    "product_id": "qxjx5jms",
    "product_name": "WUN-AXDL-261",
}

STATUS_LOCKED = {
    "lock_motor_state": False,
    "residual_electricity": 87,
    "closed_opened": "closed",
    "reverse_lock": False,
}


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    return


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="abc123",
        data={"client_id": "abc123", "client_secret": "s", "region": "eu"},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def api():
    """A TuyaLockApi stand-in, patched in wherever the integration builds one."""
    mock = AsyncMock()
    mock.list_locks.return_value = [LOCK_INFO]
    mock.get_status.return_value = dict(STATUS_LOCKED)
    with (
        patch("custom_components.tuya_ble_lock.TuyaLockApi", return_value=mock),
        patch("custom_components.tuya_ble_lock.config_flow.TuyaLockApi", return_value=mock),
    ):
        yield mock
