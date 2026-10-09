"""Minimal Tuya Cloud client for Smart Lock devices. No Home Assistant imports."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import aiohttp

REGIONS = {
    "cn": "https://openapi.tuyacn.com",
    "us-west": "https://openapi.tuyaus.com",
    "us-east": "https://openapi-ueaz.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "eu-west": "https://openapi-weaz.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
}

LOCK_CATEGORY = "jtmspro"
_TIMEOUT = aiohttp.ClientTimeout(total=15)
_TOKEN_INVALID = 1010
_PAGE_SIZE = 50


class TuyaError(Exception):
    """Base class for Tuya Cloud errors."""


class TuyaConnectionError(TuyaError):
    """The cloud could not be reached."""


class TuyaAuthError(TuyaError):
    """The Access ID / Secret / Region were rejected."""


class TuyaApiError(TuyaError):
    """The cloud answered with success=false."""

    def __init__(self, code: int | None, msg: str | None) -> None:
        super().__init__(f"Tuya error {code}: {msg}")
        self.code = code
        self.msg = msg


def sign(
    client_id: str,
    secret: str,
    method: str,
    path: str,
    body: str,
    t: str,
    token: str = "",
) -> str:
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    string_to_sign = "\n".join([method, content_hash, "", path])
    return (
        hmac.new(
            secret.encode(),
            (client_id + token + t + string_to_sign).encode(),
            hashlib.sha256,
        )
        .hexdigest()
        .upper()
    )


class TuyaLockApi:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        region: str,
    ) -> None:
        if region not in REGIONS:
            raise ValueError(f"Unknown region: {region}")
        self._session = session
        self._client_id = client_id
        self._secret = client_secret
        self._base = REGIONS[region]
        self._token = ""
        self._token_expires = 0.0

    async def authenticate(self) -> None:
        await self._fetch_token()

    async def list_locks(self) -> list[dict[str, Any]]:
        locks: list[dict[str, Any]] = []
        last_row_key = ""
        while True:
            result = await self._request(
                "GET",
                f"/v1.0/iot-01/associated-users/devices"
                f"?last_row_key={last_row_key}&page_size={_PAGE_SIZE}",
            )
            locks += [
                d for d in result.get("devices", []) if d.get("category") == LOCK_CATEGORY
            ]
            if not result.get("has_more"):
                return locks
            last_row_key = result["last_row_key"]

    async def get_status(self, device_id: str) -> dict[str, Any]:
        result = await self._request("GET", f"/v1.0/devices/{device_id}/status")
        return {s["code"]: s["value"] for s in result}

    async def remote_unlock_enabled(self, device_id: str) -> bool:
        # Response shape is from Tuya's docs and unconfirmed against a real Lock.
        result = await self._request(
            "GET", f"/v1.0/devices/{device_id}/door-lock/remote-unlocks"
        )
        return any(
            item.get("remote_unlock_type") == "remoteUnlockWithoutPwd" and item.get("open")
            for item in result
        )

    async def operate(self, device_id: str, open_: bool) -> None:
        ticket = await self._request(
            "POST", f"/v1.0/devices/{device_id}/door-lock/password-ticket", {}
        )
        await self._request(
            "POST",
            f"/v1.0/smart-lock/devices/{device_id}/password-free/door-operate",
            {"ticket_id": ticket["ticket_id"], "open": open_},
        )

    async def _fetch_token(self) -> str:
        path = "/v1.0/token?grant_type=1"
        t = str(int(time.time() * 1000))
        headers = {
            "client_id": self._client_id,
            "sign": sign(self._client_id, self._secret, "GET", path, "", t),
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        data = await self._send("GET", path, None, headers)
        if not data.get("success"):
            raise TuyaAuthError(f"Tuya rejected the credentials: {data.get('msg')}")
        result = data["result"]
        self._token = result["access_token"]
        self._token_expires = time.time() + result.get("expire_time", 7200) - 300
        return self._token

    async def _request(
        self, method: str, path: str, body: dict | None = None, *, retry: bool = True
    ) -> Any:
        if self._token and self._token_expires > time.time():
            token = self._token
        else:
            token = await self._fetch_token()
        body_str = json.dumps(body) if body is not None else ""
        t = str(int(time.time() * 1000))
        headers = {
            "client_id": self._client_id,
            "access_token": token,
            "sign": sign(self._client_id, self._secret, method, path, body_str, t, token),
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        if body_str:
            headers["Content-Type"] = "application/json"
        data = await self._send(method, path, body_str, headers)
        if data.get("success"):
            return data.get("result")
        if data.get("code") == _TOKEN_INVALID and retry:
            self._token_expires = 0.0
            return await self._request(method, path, body, retry=False)
        raise TuyaApiError(data.get("code"), data.get("msg"))

    async def _send(
        self, method: str, path: str, body: str | None, headers: dict[str, str]
    ) -> dict[str, Any]:
        try:
            async with self._session.request(
                method,
                self._base + path,
                data=body.encode() if body else None,
                headers=headers,
                timeout=_TIMEOUT,
            ) as resp:
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise TuyaConnectionError(str(err)) from err
