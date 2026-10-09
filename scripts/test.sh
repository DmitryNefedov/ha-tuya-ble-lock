#!/bin/sh
# Runs pytest in a python:3.13 container (the full image: lru-dict needs gcc). TUYA_* variables are passed through from the
# environment and never written to disk. Usage: scripts/test.sh [pytest args]
set -eu
cd "$(dirname "$0")/.."
exec docker run --rm \
  -v "$PWD":/src -w /src \
  -v tuya-ble-lock-pipcache:/root/.cache/pip \
  -e TUYA_ACCESS_ID -e TUYA_ACCESS_SECRET -e TUYA_REGION -e TUYA_DEVICE_ID \
  python:3.13 \
  sh -c 'pip install -q -r requirements_test.txt && exec pytest "$@"' sh "$@"
