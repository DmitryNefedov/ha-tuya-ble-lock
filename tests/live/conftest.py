import os

import aiohttp
import pytest
from pytest_socket import enable_socket, socket_allow_hosts

from custom_components.tuya_ble_lock.api import REGIONS, TuyaLockApi

REQUIRED = ("TUYA_ACCESS_ID", "TUYA_ACCESS_SECRET", "TUYA_REGION", "TUYA_DEVICE_ID")


@pytest.fixture(autouse=True)
def _enable_custom_integrations():
    """Live tests do not start Home Assistant; override the autouse fixture in tests/conftest.py."""


@pytest.fixture(autouse=True)
def _allow_tuya_host():
    """HA's pytest plugin blocks all sockets but localhost; allow only the Tuya API host."""
    region = os.environ.get("TUYA_REGION")
    if region in REGIONS:
        enable_socket()
        socket_allow_hosts([REGIONS[region].removeprefix("https://")])
    yield


@pytest.fixture
def device_id():
    missing = [v for v in REQUIRED if not os.environ.get(v)]
    if missing:
        pytest.skip(f"Live tests need these environment variables: {', '.join(missing)}")
    return os.environ["TUYA_DEVICE_ID"]


@pytest.fixture
async def api(device_id):
    async with aiohttp.ClientSession() as session:
        yield TuyaLockApi(
            session,
            os.environ["TUYA_ACCESS_ID"],
            os.environ["TUYA_ACCESS_SECRET"],
            os.environ["TUYA_REGION"],
        )
