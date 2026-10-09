# Plan: Tuya BLE Lock (Cloud)

Goal: a HACS custom integration that locks and unlocks the WUN-AXDL-261 (qxjx5jms, `jtmspro`) Lock and any other `jtmspro` Lock through Tuya Cloud. It starts from `rkalandyk/ha-tuya-la-lock`. See [CONTEXT.md](../CONTEXT.md) for terms and [ADR 0001](adr/0001-cloud-api-not-local-ble.md) for why it uses the cloud.

## Decisions

| # | Decision |
|---|----------|
| Repo | `github.com/DmitryNefedov/ha-tuya-ble-lock` (existing, empty). Upstream history is pushed in and `upstream` is kept as a remote. Not a GitHub fork. |
| Domain / name | `tuya_ble_lock` / "Tuya BLE Lock (Cloud)" |
| Scope | Any `jtmspro` Lock, plus a table of Verified models (`8gza4o8a`, `99gv5nmz` from upstream; `qxjx5jms` after a Live test) |
| Region | Config-flow dropdown, default Central Europe: CN `openapi.tuyacn.com`, US-West `openapi.tuyaus.com`, US-East `openapi-ueaz.tuyaus.com`, EU-Central `openapi.tuyaeu.com`, EU-West `openapi-weaz.tuyaeu.com`, India `openapi.tuyain.com` |
| Lock/unlock | Both use `POST /v1.0/devices/{id}/door-lock/password-ticket` → `POST /v1.0/smart-lock/devices/{id}/password-free/door-operate {ticket_id, open}`. A rejected command raises `HomeAssistantError`. |
| Entities | `lock`; battery `sensor` (`residual_electricity`); door `binary_sensor` (`closed_opened`) and double-lock `binary_sensor` (`reverse_lock`), each created only if the data point is present in the status |
| Updates | Polling, interval set in the options flow (30–300s, default 60). Device list is fetched at setup only. |
| Layering | `api.py` is plain aiohttp with no HA imports (signing, token, Ticket, door-operate, status, remote-unlock check). The coordinator wraps it. |
| Tests | Offline unit tests always run. Live tests live in `live_tests/`, run only via `scripts/live.sh` with env credentials, need no Home Assistant, physically unlock then lock, and are never exposed in HA. |
| HACS | Custom repository only. GitHub releases; CI runs `hacs/action` + `hassfest` + unit tests. Min HA 2025.1, Python 3.13. |
| License | None until upstream answers the license issue |
| Old work | `/mnt/data/projects/ha_tuya_ble` branch `add-qxjx5jms` is superseded and left alone |

## Phases

1. **Bootstrap repo**
   - Full (non-shallow) clone of upstream; `git init` in this directory with CONTEXT.md and docs.
   - Set `origin` = your repo and `upstream` = rkalandyk; push `main` with upstream history.
   - Open an issue upstream asking for a license.
   - → verify: `git log` shows upstream commits, plus ours, on `origin/main`.
2. **Rename and restructure**
   - `custom_components/tuya_la_lock` → `custom_components/tuya_ble_lock`; update `manifest.json`, `hacs.json`, `strings.json`/`translations/en.json`.
   - Translate the Polish comments and logs to English.
   - Fix the README/code ticket-endpoint mismatch.
   - → verify: `hassfest` passes.
3. **Extract `api.py`** (`TuyaLockApi(session, client_id, secret, region)`)
   - Move signing and token caching out of the coordinator and config flow, removing the duplicated signing code.
   - Add `region` → base URL, `list_locks()`, `get_status()`, `remote_unlock_enabled()` (`GET /v1.0/devices/{id}/door-lock/remote-unlocks`, verify shape on the first live run), and `operate(open: bool)`.
   - → verify: unit tests sign a known vector and handle token refresh and every API error path (aioresponses).
4. **Config and options flow**
   - Fields: Access ID, Access Secret, Region (default EU-Central). Auth is tested through `api.py`.
   - Options flow: poll interval.
   - → verify: config-flow tests cover success, bad auth, duplicate entry, and options.
5. **Entities**
   - `lock` with `async_lock`/`async_unlock` → `operate(False/True)`, then refresh.
   - `is_locked` comes from the lock-state data point, confirmed in Phase 7 (`lock_motor_state` assumed).
   - Battery sensor; conditional binary sensors.
   - Remove upstream's always-`True` default for `is_locked`, so a missing data point shows as unknown.
   - → verify: entity tests with recorded status fixtures.
6. **Test harness**
   - `requirements_test.txt` (`pytest-homeassistant-custom-component`, `aioresponses`).
   - `live_tests/` uses only `api.py` (loaded by file path, so no Home Assistant import) + aiohttp, with its own slim image.
   - `scripts/test.sh` runs the offline tests in a cached `python:3.13` image (gcc is needed for `lru-dict`).
   - `scripts/live.sh` runs the Live tests and passes `TUYA_*` env vars through without writing them anywhere.
   - → verify: offline suite green; `scripts/live.sh` without env vars skips with the reason shown.
7. **Live tests** (env: `TUYA_ACCESS_ID`, `TUYA_ACCESS_SECRET`, `TUYA_REGION`, `TUYA_DEVICE_ID`)
   - Token and device list: the Lock is found with category `jtmspro`.
   - Status dump, printed for the data-point mapping in Phase 5.
   - Remote unlock enabled: otherwise stop with a message pointing to Smart Life → Lock → Settings → Remote Unlock.
   - Physical cycle:
     - refuse to start unless the Lock reports Locked
     - unlock and poll until Unlocked (30s)
     - lock and poll until Locked (30s)
     - cleanup always attempts lock
   - → verify: run once by you against WUN-AXDL-261. On success, add `qxjx5jms` to Verified models.
8. **HACS and release**
   - CI workflow (hacs/action, hassfest, pytest offline).
   - README: install as a HACS custom repo; Tuya IoT setup (Smart Lock API subscription, linking the app account, Region); entities; running Live tests.
   - Tag `v0.1.0` and create a GitHub release.
   - → verify: CI green; install via HACS on HAOS VM 100, and the Lock locks and unlocks from HA.

## Open risks

- qxjx5jms may reject `door-operate` with `open:false`. Phase 7 finds out; fallback is unlock-only, with lock raising a clear error.
- The lock-state data-point code and its values are unconfirmed until the first live status dump.
- Trial Tuya IoT projects expire and have API quotas, which the README must explain.
