#!/usr/bin/env bash
set -euo pipefail

echo "Stopping container..."
docker stop pm-app-container >/dev/null 2>&1 || true

echo "Removing container..."
docker rm pm-app-container >/dev/null 2>&1 || true

echo "Stopped pm-app-container."
