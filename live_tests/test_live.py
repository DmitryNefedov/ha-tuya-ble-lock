"""Live tests: talk to Tuya Cloud and physically operate a real Lock.

Independent of Home Assistant. Run with: TUYA_ACCESS_ID=... TUYA_ACCESS_SECRET=... \
TUYA_REGION=eu TUYA_DEVICE_ID=... scripts/live.sh
"""

import asyncio
import json
import time

import pytest

POLL_TIMEOUT = 30
POLL_EVERY = 2


def is_locked(status):
    # Mirrors TuyaLock.is_locked in lock.py: lock_motor_state is True while the bolt is retracted.
    motor = status.get("lock_motor_state")
    assert isinstance(motor, bool), f"lock_motor_state missing or not a bool; status: {status}"
    return not motor


async def wait_until(api, device_id, locked):
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        status = await api.get_status(device_id)
        if is_locked(status) is locked:
            return
        if time.monotonic() > deadline:
            pytest.fail(
                f"Lock did not become {'Locked' if locked else 'Unlocked'} "
                f"within {POLL_TIMEOUT}s; status: {status}"
            )
        await asyncio.sleep(POLL_EVERY)


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
    assert await api.remote_unlock_enabled(device_id), (
        "Remote unlock is off. Enable it in Smart Life → Lock → Settings → Remote Unlock."
    )


async def test_physical_cycle(api, device_id):
    assert await api.remote_unlock_enabled(device_id), (
        "Remote unlock is off. Enable it in Smart Life → Lock → Settings → Remote Unlock."
    )
    assert is_locked(await api.get_status(device_id)), (
        "Refusing to start: the Lock must report Locked first."
    )
    try:
        await api.operate(device_id, True)
        await wait_until(api, device_id, locked=False)
        await api.operate(device_id, False)
        await wait_until(api, device_id, locked=True)
    finally:
        try:
            await api.operate(device_id, False)
        except Exception as err:  # noqa: BLE001 - best effort, original failure matters more
            print(f"Cleanup lock failed: {err}")
