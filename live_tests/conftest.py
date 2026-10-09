import importlib.util
import os
from pathlib import Path

import aiohttp
import pytest

REQUIRED = ("TUYA_ACCESS_ID", "TUYA_ACCESS_SECRET", "TUYA_REGION", "TUYA_DEVICE_ID")
API_FILE = Path(__file__).parent.parent / "custom_components" / "tuya_ble_lock" / "api.py"

# Load api.py by path: importing the package would pull in Home Assistant.
_spec = importlib.util.spec_from_file_location("tuya_lock_api", API_FILE)
tuya_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tuya_api)


@pytest.fixture
def device_id():
    missing = [v for v in REQUIRED if not os.environ.get(v)]
    if missing:
        pytest.skip(f"Live tests need these environment variables: {', '.join(missing)}")
    return os.environ["TUYA_DEVICE_ID"]


@pytest.fixture
async def api(device_id):
    async with aiohttp.ClientSession() as session:
        yield tuya_api.TuyaLockApi(
            session,
            os.environ["TUYA_ACCESS_ID"],
            os.environ["TUYA_ACCESS_SECRET"],
            os.environ["TUYA_REGION"],
        )
