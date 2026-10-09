# Tuya BLE Lock (Cloud)

Home Assistant integration that controls Tuya Bluetooth door locks through Tuya Cloud, relayed by a Tuya Bluetooth Gateway.

## Language

**Lock**:
A Tuya door lock in the `jtmspro` category, reachable only over Bluetooth and registered in Tuya Cloud as a sub-device of a Gateway.
_Avoid_: door, device (too generic)

**Gateway**:
The Tuya Bluetooth Gateway hardware that relays Cloud commands to Locks over Bluetooth. Home Assistant never talks to it directly.
_Avoid_: bridge, hub, BLE adapter

**Region**:
The Tuya Cloud data center that hosts the user's account (e.g. Central Europe). It determines the API endpoint.
_Avoid_: server, endpoint, datacenter (in UI text)

**Ticket**:
A single-use authorisation token from Tuya Cloud that must be presented to lock or unlock a Lock.

**Verified model**:
A Lock product ID that a real Live test has confirmed to unlock and lock correctly.

**Live test**:
A test run by a developer against a real Lock with credentials from the environment. It physically unlocks and re-locks the Lock and is never exposed inside Home Assistant.
_Avoid_: integration test, e2e test

## Relationships

- A **Gateway** relays commands to one or more **Locks**
- Each **Lock** belongs to exactly one **Region** (the account's)
- Each lock or unlock command uses one fresh **Ticket**

## Flagged ambiguities

- "Gateway passed to the VM": the Proxmox USB passthrough (`10c4:ea60`, a CP210x serial bridge) is not the **Gateway** and plays no part in this integration.
