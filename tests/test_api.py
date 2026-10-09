"""Offline unit tests for the Tuya Cloud client."""

from types import SimpleNamespace

import aiohttp
import pytest
from aioresponses import aioresponses

import custom_components.tuya_ble_lock.api as api_module
from custom_components.tuya_ble_lock.api import (
    TuyaApiError,
    TuyaAuthError,
    TuyaConnectionError,
    TuyaLockApi,
    is_locked,
    sign,
)

BASE = "https://openapi.tuyaeu.com"
TOKEN_URL = f"{BASE}/v1.0/token?grant_type=1"
TOKEN_OK = {
    "success": True,
    "result": {"access_token": "tok", "expire_time": 7200, "refresh_token": "r"},
}


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def mocked():
    with aioresponses() as m:
        yield m


def _calls(mocked, path_suffix):
    return next(c for (_, url), c in mocked.requests.items() if url.path.endswith(path_suffix))


@pytest.fixture
def api(session):
    return TuyaLockApi(session, "abc123", "secret456", "eu")


def test_sign_token_request_known_vector():
    assert (
        sign("abc123", "secret456", "GET", "/v1.0/token?grant_type=1", "", "1700000000000")
        == "2D2386EF2B9C1FFD7816DF37D1023482B44F9DD74F5D569C3AF7B5F9C0CF651B"
    )


def test_sign_authenticated_request_known_vector():
    assert (
        sign("abc123", "secret456", "POST", "/v1.0/x", "{}", "1700000000000", "tok")
        == "AB49A32E382210E2CB2A046D6368282D7954FF6552F9E1050845A51D429D1881"
    )


def test_unknown_region_rejected(session):
    with pytest.raises(ValueError):
        TuyaLockApi(session, "a", "b", "mars")


async def test_authenticate_ok(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    await api.authenticate()


async def test_authenticate_bad_credentials(api, mocked):
    mocked.get(TOKEN_URL, payload={"success": False, "code": 1004, "msg": "sign invalid"})
    with pytest.raises(TuyaAuthError):
        await api.authenticate()


async def test_authenticate_invalid_client_id(api, mocked):
    mocked.get(TOKEN_URL, payload={"success": False, "code": 2009, "msg": "clientId is invalid"})
    with pytest.raises(TuyaAuthError):
        await api.authenticate()


async def test_authenticate_other_tuya_error_is_not_a_credential_error(api, mocked):
    mocked.get(
        TOKEN_URL,
        payload={"success": False, "code": 28841002, "msg": "IoT Core service subscription has expired."},
    )
    with pytest.raises(TuyaApiError) as err:
        await api.authenticate()
    assert not isinstance(err.value, TuyaAuthError)
    assert err.value.code == 28841002


async def test_authenticate_network_error(api, mocked):
    mocked.get(TOKEN_URL, exception=aiohttp.ClientConnectionError("down"))
    with pytest.raises(TuyaConnectionError):
        await api.authenticate()


async def test_authenticate_timeout(api, mocked):
    mocked.get(TOKEN_URL, exception=TimeoutError())
    with pytest.raises(TuyaConnectionError):
        await api.authenticate()


async def test_token_is_cached(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)  # only registered once
    mocked.get(f"{BASE}/v1.0/devices/d1/status", payload={"success": True, "result": []}, repeat=True)
    await api.get_status("d1")
    await api.get_status("d1")


async def test_token_refetched_after_it_expires(session, mocked, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(api_module, "time", SimpleNamespace(time=lambda: now[0]))
    api = TuyaLockApi(session, "abc123", "secret456", "eu")
    status_url = f"{BASE}/v1.0/devices/d1/status"
    ok = {"success": True, "result": []}
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(status_url, payload=ok, repeat=True)
    await api.get_status("d1")
    now[0] = 1000 + 7200 - 301  # still inside the 5 minute safety margin
    await api.get_status("d1")
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    now[0] = 1000 + 7200  # past expiry minus margin
    await api.get_status("d1")
    token_calls = [c for (_, url), c in mocked.requests.items() if url.path == "/v1.0/token"]
    assert sum(len(c) for c in token_calls) == 2


async def test_token_refreshed_after_server_says_invalid(api, mocked):
    status_url = f"{BASE}/v1.0/devices/d1/status"
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(status_url, payload={"success": False, "code": 1010, "msg": "token invalid"})
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(status_url, payload={"success": True, "result": [{"code": "a", "value": 1}]})
    assert await api.get_status("d1") == {"a": 1}


async def test_requests_are_signed(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(f"{BASE}/v1.0/devices/d1/status", payload={"success": True, "result": []})
    await api.get_status("d1")
    headers = _calls(mocked, "/status")[0].kwargs["headers"]
    assert headers["client_id"] == "abc123"
    assert headers["access_token"] == "tok"
    assert headers["sign_method"] == "HMAC-SHA256"
    assert headers["sign"] == sign(
        "abc123", "secret456", "GET", "/v1.0/devices/d1/status", "", headers["t"], "tok"
    )


async def test_regional_base_url(session, mocked):
    mocked.get("https://openapi.tuyaus.com/v1.0/token?grant_type=1", payload=TOKEN_OK)
    await TuyaLockApi(session, "a", "b", "us-west").authenticate()


async def test_api_error_raised(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(
        f"{BASE}/v1.0/devices/d1/status",
        payload={"success": False, "code": 2001, "msg": "permission deny"},
    )
    with pytest.raises(TuyaApiError) as err:
        await api.get_status("d1")
    assert err.value.code == 2001
    assert "permission deny" in str(err.value)


async def test_api_network_error(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(f"{BASE}/v1.0/devices/d1/status", exception=aiohttp.ClientError("boom"))
    with pytest.raises(TuyaConnectionError):
        await api.get_status("d1")


async def test_list_locks_filters_category_and_paginates(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    base = f"{BASE}/v1.0/iot-01/associated-users/devices"
    mocked.get(
        f"{base}?last_row_key=&page_size=50",
        payload={
            "success": True,
            "result": {
                "devices": [
                    {"id": "lock1", "category": "jtmspro"},
                    {"id": "plug1", "category": "cz"},
                ],
                "has_more": True,
                "last_row_key": "k1",
            },
        },
    )
    mocked.get(
        f"{base}?last_row_key=k1&page_size=50",
        payload={
            "success": True,
            "result": {"devices": [{"id": "lock2", "category": "jtmspro"}], "has_more": False},
        },
    )
    assert [d["id"] for d in await api.list_locks()] == ["lock1", "lock2"]


async def test_list_locks_empty(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(
        f"{BASE}/v1.0/iot-01/associated-users/devices?last_row_key=&page_size=50",
        payload={"success": True, "result": {}},
    )
    assert await api.list_locks() == []


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ([{"remote_unlock_type": "remoteUnlockWithoutPwd", "open": True}], True),
        ([{"remote_unlock_type": "remoteUnlockWithoutPwd", "open": False}], False),
        ([{"remote_unlock_type": "remoteUnlockWithPwd", "open": True}], False),
        ([], False),
    ],
)
async def test_remote_unlock_enabled(api, mocked, result, expected):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.get(
        f"{BASE}/v1.0/devices/d1/door-lock/remote-unlocks",
        payload={"success": True, "result": result},
    )
    assert await api.remote_unlock_enabled("d1") is expected


@pytest.mark.parametrize("open_", [True, False])
async def test_operate_uses_fresh_ticket_then_door_operate(api, mocked, open_):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.post(
        f"{BASE}/v1.0/devices/d1/door-lock/password-ticket",
        payload={"success": True, "result": {"ticket_id": "t1", "expire_time": 60}},
    )
    mocked.post(
        f"{BASE}/v1.0/smart-lock/devices/d1/password-free/door-operate",
        payload={"success": True, "result": True},
    )
    await api.operate("d1", open_)
    assert _calls(mocked, "door-operate")[0].kwargs["data"] == (
        b'{"ticket_id": "t1", "open": %s}' % (b"true" if open_ else b"false")
    )


async def test_operate_ticket_rejected(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.post(
        f"{BASE}/v1.0/devices/d1/door-lock/password-ticket",
        payload={"success": False, "code": 2001, "msg": "no permission"},
    )
    with pytest.raises(TuyaApiError):
        await api.operate("d1", True)


async def test_operate_rejected(api, mocked):
    mocked.get(TOKEN_URL, payload=TOKEN_OK)
    mocked.post(
        f"{BASE}/v1.0/devices/d1/door-lock/password-ticket",
        payload={"success": True, "result": {"ticket_id": "t1"}},
    )
    mocked.post(
        f"{BASE}/v1.0/smart-lock/devices/d1/password-free/door-operate",
        payload={"success": False, "code": 2008, "msg": "remote unlock disabled"},
    )
    with pytest.raises(TuyaApiError):
        await api.operate("d1", False)


@pytest.mark.parametrize(
    ("status", "expected"),
    [({"lock_motor_state": False}, True), ({"lock_motor_state": True}, False), ({}, None), ({"lock_motor_state": "x"}, None)],
)
def test_is_locked(status, expected):
    assert is_locked(status) is expected
