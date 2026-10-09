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


async def test_event_logs(api, device_id, capsys):
    """Read-only: which Lock events do Tuya's logs record (failed fingerprint, unlocks, alarms)?"""
    now_ms = int(time.time() * 1000)
    window = f"start_time={now_ms - 24 * 3600 * 1000}&end_time={now_ms}"
    noisy = {"residual_electricity"}

    def when(ms):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ms / 1000))

    with capsys.disabled():
        print("\nData point changes, last 24 h (/v1.0/devices/{id}/logs?type=7):")
        logs, last_key = [], ""
        for _ in range(10):
            result = await api._request(
                "GET", f"/v1.0/devices/{device_id}/logs?type=7&{window}&query_type=1&size=100&last_row_key={last_key}"
            )
            logs += result.get("logs", [])
            last_key = result.get("next_row_key", "")
            if not (result.get("has_next") and last_key):
                break
        counts = {}
        for log in logs:
            counts[log["code"]] = counts.get(log["code"], 0) + 1
        print(f"  counts by data point: {json.dumps(counts, sort_keys=True)}")
        for log in sorted(logs, key=lambda x: x["event_time"]):
            if log["code"] not in noisy:
                print(f"  {when(log['event_time'])}  {log['code']} = {log['value']}")

        print("\nUnlock history (/v1.1/devices/{id}/door-lock/open-logs):")
        result = await api._request(
            "GET", f"/v1.1/devices/{device_id}/door-lock/open-logs?page_no=1&page_size=50&{window}"
        )
        for log in sorted(result.get("logs", []), key=lambda x: x["update_time"]):
            status = log["status"]
            print(f"  {when(log['update_time'])}  {status['code']} = {status['value']}  {log.get('unlock_name') or ''}")
