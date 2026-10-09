"""Live tests: talk to Tuya Cloud and send real lock and unlock commands to a Lock.

Independent of Home Assistant. Run with: TUYA_ACCESS_ID=... TUYA_ACCESS_SECRET=... \
TUYA_REGION=eu TUYA_DEVICE_ID=... scripts/live.sh
"""

import asyncio
import json
import time

import pytest

REMOTE_OFF = "Remote unlock is off. Enable it in Smart Life → Lock → Settings → Remote Unlock."
POLL_TIMEOUT = 15
POLL_EVERY = 3


def changed(before, after):
    return {k: (before.get(k), after.get(k)) for k in before.keys() | after.keys() if before.get(k) != after.get(k)}


async def send_and_watch(api, device_id, open_):
    """Send one command and print every data point that changes in the next few seconds."""
    before = await api.get_status(device_id)
    await api.operate(device_id, open_)
    print(f"\nCommand {'UNLOCK' if open_ else 'LOCK'} accepted by Tuya. Watch the door.")
    deadline = time.monotonic() + POLL_TIMEOUT
    diff = {}
    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_EVERY)
        diff = changed(before, await api.get_status(device_id))
        if diff:
            break
    print(f"Data points that changed: {json.dumps(diff, indent=2, sort_keys=True) if diff else 'none (status is not live for this Lock)'}")


async def test_token_and_device_list(api, device_id):
    await api.authenticate()
    ids = {lock["id"]: lock for lock in await api.list_locks()}
    assert device_id in ids, f"{device_id} not among jtmspro Locks: {sorted(ids)}"
    print(f"\nLock: {json.dumps(ids[device_id], indent=2)}")


async def test_status_dump(api, device_id, capsys):
    status = await api.get_status(device_id)
    with capsys.disabled():
        print(f"\nStatus data points:\n{json.dumps(status, indent=2, sort_keys=True)}")
    assert status


async def test_remote_unlock_enabled(api, device_id):
    assert await api.remote_unlock_enabled(device_id), REMOTE_OFF


async def test_send_unlock(api, device_id):
    """Physically releases the Lock (momentary: it re-locks itself)."""
    assert await api.remote_unlock_enabled(device_id), REMOTE_OFF
    await send_and_watch(api, device_id, True)


async def test_send_lock(api, device_id):
    """Tuya may reject this for a Lock that is locked by default; that rejection is the finding."""
    assert await api.remote_unlock_enabled(device_id), REMOTE_OFF
    await send_and_watch(api, device_id, False)
