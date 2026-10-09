#!/bin/sh
# Runs the offline tests in a container with the test dependencies baked into a cached image.
# TUYA_* variables are passed through from the environment and never written to disk.
# Usage: scripts/test.sh [pytest args]
set -eu
cd "$(dirname "$0")/.."
echo "Preparing test image (slow only when requirements_test.txt changes)..." >&2
docker build -q -t tuya-ble-lock-test -f scripts/Dockerfile.test . >/dev/null
exec docker run --rm \
  -v "$PWD":/src -w /src \
  -e TUYA_ACCESS_ID -e TUYA_ACCESS_SECRET -e TUYA_REGION -e TUYA_DEVICE_ID \
  tuya-ble-lock-test pytest "$@"
