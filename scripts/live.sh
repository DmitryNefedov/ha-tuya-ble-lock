#!/bin/sh
# Runs the Live tests (they physically unlock and re-lock a real Lock) with no Home Assistant.
# TUYA_* variables are passed through from the environment and never written to disk.
# Usage: scripts/live.sh [pytest args]   e.g. scripts/live.sh -k status
set -eu
cd "$(dirname "$0")/.."
docker build -q -t tuya-ble-lock-live -f live_tests/Dockerfile . >/dev/null
exec docker run --rm \
  -v "$PWD":/src -w /src/live_tests \
  -e TUYA_ACCESS_ID -e TUYA_ACCESS_SECRET -e TUYA_REGION -e TUYA_DEVICE_ID \
  tuya-ble-lock-live pytest -s "$@"
