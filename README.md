# Tuya BLE Lock (Cloud)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DmitryNefedov&repository=ha-tuya-ble-lock&category=integration)
[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tuya_ble_lock)

[![HACS: Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/DmitryNefedov/ha-tuya-ble-lock/actions/workflows/validate.yml/badge.svg)](https://github.com/DmitryNefedov/ha-tuya-ble-lock/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/DmitryNefedov/ha-tuya-ble-lock)](https://github.com/DmitryNefedov/ha-tuya-ble-lock/releases)

Home Assistant integration that locks and unlocks Tuya Bluetooth door locks (category `jtmspro`) through Tuya Cloud, relayed by a Tuya Bluetooth Gateway. Home Assistant does not need Bluetooth. See [ADR 0001](docs/adr/0001-cloud-api-not-local-ble.md).

**Built and verified on the Aldi Delta Smart Bluetooth door handle lock** (model WUN-AXDL-261, Tuya product ID `qxjx5jms`). Other `jtmspro` locks should work too; see [Supported hardware](#supported-hardware).

Started from [rkalandyk/ha-tuya-la-lock](https://github.com/rkalandyk/ha-tuya-la-lock).

## Requirements

- A Tuya Bluetooth Gateway in range of the lock, with the lock added to it in the Smart Life app. The lock is only reachable through the Gateway.
- A free [Tuya IoT](https://iot.tuya.com) developer account and Cloud project, set up as described in [Tuya Cloud setup](#tuya-cloud-setup).
- Home Assistant 2025.1 or newer, with [HACS](https://hacs.xyz) installed.

## Install with HACS (from GitHub)

1. Click the **HACS repository** button above, or in HACS open the three-dot menu → **Custom repositories** and add `https://github.com/DmitryNefedov/ha-tuya-ble-lock` with type **Integration**.
2. Install **Tuya BLE Lock (Cloud)** and restart Home Assistant.
3. Click the **Set up integration** button above, or go to Settings → Devices & services → Add integration → **Tuya BLE Lock (Cloud)**. Enter the Access ID, Access Secret and Region from your Tuya project.

## Tuya Cloud setup

The integration (and the live tests below) call the Tuya Cloud API with a project of your own. Do this once:

1. Sign in at [iot.tuya.com](https://iot.tuya.com) and open **Cloud → Development → Create Cloud Project**.
   - **Data Center:** the one your Smart Life account lives in (this is the Region you enter later). Central Europe is `eu`.
   - **Development Method:** Smart Home.
2. On the project's **Service API** tab, subscribe to the APIs it needs:
   - **IoT Core** (device list and status). Without it Tuya answers `28841002: IoT Core service subscription has expired`.
   - **Smart Lock Open Service** (tickets and unlocking). The name can differ slightly between data centers; search the list for "lock".
   - **Authorization Token Management** (usually already included).
3. Link your Smart Life account to the project: **Devices → Link App Account → Add App Account**, then scan the QR code in the Smart Life app (Me → scan icon). The lock appears under **Devices → All Devices**.
4. In the Smart Life app, open the lock → Settings and enable **Remote Unlock**. Without it Tuya rejects commands.

Free subscriptions are trials. When one expires, extend it from the **Service API** tab (the error code above is how an expired one shows up). Trials also have API quotas.

### Where to find the values

| Value | Where | Used as |
|-------|-------|---------|
| Access ID | Project → **Overview** → Authorization Key (called Access ID / Client ID) | `TUYA_ACCESS_ID` |
| Access Secret | Same place (click the eye icon) | `TUYA_ACCESS_SECRET` |
| Region | The project's Data Center | `TUYA_REGION`: `cn`, `us-west`, `us-east`, `eu`, `eu-west`, `in` |
| Device ID | Project → **Devices → All Devices**, or the Smart Life app's device information page for the lock (wording varies by app version) | `TUYA_DEVICE_ID` |

## Entities

| Entity | Notes |
|--------|-------|
| `lock` | Lock and unlock. State comes from `lock_motor_state` (`false` is locked, `true` is unlocked). |
| `sensor` Battery | From `residual_electricity`. The reading is noisy (it moves several points while the motor runs). |
| `binary_sensor` Door | From `closed_opened`. This lock reports `unknown`, so expect an unknown state. |
| `binary_sensor` Double locked | From `reverse_lock`. |
| `sensor` Last unlock | When and how the lock was last unlocked in the last 7 days. Attributes: `method` (`unlock_fingerprint`, `unlock_phone_remote`, `unlock_ble`...), `name` (the finger or code name, for example "Left Thumb") and `user`. Read from Tuya's unlock history, at most every 30 minutes and once after each command. |

Behaviour specific to this lock:
- **It re-locks itself.** The Delta Smart handle is locked by default and releases only briefly after an unlock (fingerprint, code, or this integration). The state returns to locked on its own about 6 seconds after the unlock.
- **It unlocks slowly.** After a command the lock releases about 10 seconds later and re-locks about 6 seconds after that. Home Assistant reads the state again 12 and 20 seconds after each command, so both changes show up. See [Polling and Tuya's API limit](#polling-and-tuyas-api-limit).
- **The state can lag.** Between polls Home Assistant does not know what happened at the door. A fingerprint unlock lasts about 6 seconds, so a poll will usually miss it.
- **Failed fingerprints are not reported.** Tuya records successful unlocks, with the finger name, but nothing for a rejected fingerprint; `alarm_lock` in the status is a stale value.
- **Offline is not detected.** The device list is read once when the integration loads (reload it after adding a lock), and the lock does not turn "unavailable" when the Gateway goes offline; commands will then fail with an error.

## Polling and Tuya's API limit

Tuya's free IoT Core trial allows **26,000 API calls a month**, in total. Polling every minute around the clock would use about 43,000 calls on status alone, so the integration polls on a fixed schedule in Home Assistant's timezone (Settings → System → General):

| Local time | Status poll |
|------------|-------------|
| 07:30–10:00 | every 1 minute |
| 10:00–15:00 | every 30 minutes |
| 15:00–18:30 | every 1 minute |
| 18:30–07:30 | every 30 minutes |

Why these hours: they are when people typically come and go, so a fresh state matters most then. The rest of the day it barely does, because the unlocked state lasts only about 6 seconds.

Monthly budget (30 days):

| Calls | Per month |
|-------|-----------|
| Status polls (396 a day) | 11,880 |
| Unlock history (every 30 minutes, 48 a day) | 1,440 |
| Commands (5 calls each, 20 a day) | 3,000 |
| **Total** | **about 16,300** of 26,000 |

A command costs 5 calls: the ticket, the unlock, a status read at 12 s, another at 20 s, and one unlock-history read. The Last unlock sensor therefore updates at most every 30 minutes, or right after a command.

**The schedule is not configurable yet.** It is fixed in code (`custom_components/tuya_ble_lock/schedule.py`); an options screen is planned. The live tests and every reload also use calls from the same quota.

## How locking works

Each command first requests a single-use ticket, then operates the lock with it:

```
POST /v1.0/devices/{id}/door-lock/password-ticket              → { ticket_id }
POST /v1.0/smart-lock/devices/{id}/password-free/door-operate  { ticket_id, open: true|false }
```

A command Tuya rejects raises an error in Home Assistant. Tuya accepted both `open: true` and `open: false` on the Delta Smart lock.

## Supported hardware

Any `jtmspro` lock should work. A model is **verified** once a [live test](#live-tests-real-lock) has unlocked and locked a real lock.

| Product ID | Model | Verified |
|------------|-------|----------|
| `qxjx5jms` | Aldi Delta Smart Bluetooth door handle lock (WUN-AXDL-261) | yes, unlock and lock (live test) |
| `8gza4o8a` | LA-T01 | by upstream |
| `99gv5nmz` | LA-T01 (variant) | by upstream |

## Development

Everything runs in Docker (no local Python needed).

```
scripts/test.sh            # offline unit tests (Home Assistant test harness)
```

The first run builds an image with the dependencies, which takes a few minutes; later runs start in seconds. CI (`.github/workflows/validate.yml`) runs the HACS action, hassfest and these tests.

## Live tests (real lock)

Live tests talk to the real Tuya Cloud and **send real unlock and lock commands to your door**. They live in `live_tests/`, are independent of Home Assistant (they load `api.py` directly and run in a small `python:3.13-slim` image with pytest and aiohttp), are never part of `scripts/test.sh` or CI, and read credentials only from environment variables (nothing is written to disk).

### Requirements

- Docker.
- Internet access to your Region's Tuya API host.
- A Tuya Cloud project set up as in [Tuya Cloud setup](#tuya-cloud-setup): IoT Core and Smart Lock subscriptions active, the Smart Life account linked, and **Remote Unlock enabled** on the lock.
- The Gateway online and the lock added to it.
- You standing at the door for the two command tests.

### Run

```bash
export TUYA_ACCESS_ID=...            # Project → Overview
export TUYA_ACCESS_SECRET=...
export TUYA_REGION=eu                # cn, us-west, us-east, eu, eu-west or in
export TUYA_DEVICE_ID=...            # the lock's device ID

scripts/live.sh                      # all tests
scripts/live.sh -k status            # one test: token, status, last_unlock, remote, send_unlock, send_lock or event_logs
```

Without the four variables every test skips and says which are missing.

### What each test does

| Test | Moves the door? | What it checks |
|------|-----------------|----------------|
| `token` | no | Credentials and Region work, and your lock is in the account's `jtmspro` device list. |
| `status` | no | Prints all of the lock's data points. |
| `last_unlock` | no | Prints the lock's most recent unlock from the unlock history (what the Last unlock sensor shows). |
| `remote` | no | Remote Unlock is enabled on the lock. |
| `send_unlock` | **yes** | Sends an unlock. The handle releases for a few seconds, then re-locks itself. Prints which data points changed. |
| `send_lock` | no (it is already locked) | Sends a lock and prints which data points changed. |
| `event_logs` | no | Read-only probe of Tuya's log endpoints (last 24 h) to see whether unlock and failed-fingerprint events are recorded. |

Expected results on the Aldi Delta Smart lock: both commands are accepted; `lock_motor_state` goes `false → true` after an unlock and back to `false` after a lock. If nothing in the status changes, the cloud has not heard back from the lock yet; run `status` again after a minute.

### When it fails

| Error | Cause |
|-------|-------|
| `clientId is invalid` / `sign invalid` | Wrong Access ID or Secret, or the wrong Region. |
| `IoT Core service subscription has expired` | Extend the IoT Core trial on the project's Service API tab. |
| `permission deny` | A required API is not subscribed, or the Smart Life account is not linked to the project. |
| `Remote unlock is off` | Enable Remote Unlock on the lock in Smart Life. |
| `not among jtmspro Locks` | Wrong `TUYA_DEVICE_ID`, or the lock is not in the linked account. |

## License

None yet. Upstream has not published a license.
