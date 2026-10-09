# Tuya BLE Lock (Cloud)

Home Assistant integration that locks and unlocks Tuya Bluetooth door locks (category `jtmspro`) through Tuya Cloud, relayed by a Tuya Bluetooth Gateway. It does not use Bluetooth from Home Assistant. See [ADR 0001](docs/adr/0001-cloud-api-not-local-ble.md).

Started from [rkalandyk/ha-tuya-la-lock](https://github.com/rkalandyk/ha-tuya-la-lock).

## Setup

### Tuya IoT project
1. Create a Cloud project at [iot.tuya.com](https://iot.tuya.com) in the Data Center (Region) of your Smart Life account.
2. Subscribe the project to the **Smart Lock** API (Cloud → your project → Service API).
3. Link your Smart Life account to the project (Devices → Link App Account).
4. In the Smart Life app, enable **Remote Unlock** for the Lock (Lock → Settings → Remote Unlock).

Trial projects expire and have API quotas; renew the trial or subscribe to a paid plan if commands start failing.

### Install
1. HACS → Custom repositories → add `https://github.com/DmitryNefedov/ha-tuya-ble-lock` as an Integration.
2. Install **Tuya BLE Lock (Cloud)**, restart Home Assistant.
3. Settings → Devices & services → Add integration → **Tuya BLE Lock (Cloud)**. Enter the project's Access ID, Access Secret and Region.

Requires Home Assistant 2025.1 or newer.

## Entities

| Entity | Notes |
|--------|-------|
| `lock` | Lock and unlock. State comes from the `lock_motor_state` data point. |
| `sensor` Battery | From `residual_electricity`. |
| `binary_sensor` Door | From `closed_opened`. Only if the Lock reports it. |
| `binary_sensor` Double locked | From `reverse_lock`. Only if the Lock reports it. |

State is polled (default every 60 s, 30–300 s in the integration's options), so changes made outside Home Assistant show up late. The device list is read once when the integration loads; reload the integration after adding a Lock.

## How locking works

Each command first requests a single-use ticket, then operates the Lock with it:

```
POST /v1.0/devices/{id}/door-lock/password-ticket              → { ticket_id }
POST /v1.0/smart-lock/devices/{id}/password-free/door-operate  { ticket_id, open: true|false }
```

A command the cloud rejects raises an error in Home Assistant.

## Supported hardware

Any `jtmspro` Lock should work. Verified models have passed a [live test](#live-tests) that unlocked and re-locked a real Lock.

| Product ID | Model | Verified |
|------------|-------|----------|
| `8gza4o8a` | LA-T01 | by upstream |
| `99gv5nmz` | LA-T01 (variant) | by upstream |
| `qxjx5jms` | WUN-AXDL-261 | yes, lock and unlock (live test) |

## Development

Tests run in Docker (`python:3.13`; the first run builds an image with the dependencies, which takes a few minutes):

```
scripts/test.sh                 # offline unit tests
```

### Live tests

These talk to Tuya Cloud and **physically unlock then re-lock a real Lock**. They live in `live_tests/`, need no Home Assistant (a small `python:3.13-slim` image with pytest and aiohttp), are never part of `scripts/test.sh`, and use only environment variables (nothing is stored):

```
TUYA_ACCESS_ID=... TUYA_ACCESS_SECRET=... TUYA_REGION=eu TUYA_DEVICE_ID=... \
  scripts/live.sh                # all five tests
  scripts/live.sh -k status      # just one: token, status, remote, send_unlock or send_lock
```

`TUYA_REGION` is one of `cn`, `us-west`, `us-east`, `eu`, `eu-west`, `in`. The tests print the Lock's data points; the physical cycle refuses to start unless the Lock reports Locked, and always attempts to lock on exit.

## License

None yet. Upstream has not published a license.
