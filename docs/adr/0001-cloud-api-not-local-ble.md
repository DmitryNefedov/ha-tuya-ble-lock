# Use the Tuya Cloud API, not local Bluetooth, despite the repo name

The WUN-AXDL-261 (qxjx5jms) Lock is reachable only through a Tuya Bluetooth Gateway, and Home Assistant's host has no Bluetooth adapter near the Lock. We therefore control Locks through Tuya Cloud's Smart Lock API (Ticket + `password-free/door-operate`), which relays commands through the Gateway. We do not talk Bluetooth locally as `ha_tuya_ble` does. An earlier local attempt (a branch of `ha-tuya-ble/ha_tuya_ble`) was abandoned: it needed the Lock's local key and a Bluetooth radio in range, and the Lock's data-point schema was unknown.

The repo is named `ha-tuya-ble-lock` because it targets Tuya *BLE locks*, not because it uses BLE. The display name "Tuya BLE Lock (Cloud)" makes that explicit.

## Consequences

- Needs internet and a Tuya IoT project subscribed to the Smart Lock API, and is subject to its API quota.
- State is polled (default 60s), so changes made outside HA show up late.
- Remote unlock must be enabled for the Lock in the Smart Life app.
