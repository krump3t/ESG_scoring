#!/usr/bin/env bash
set -euo pipefail
command -v docker >/dev/null 2>&1 || { echo "❌ Docker CLI not installed"; exit 1; }
docker info >/dev/null 2>&1 || { echo "❌ Docker Desktop/daemon not running"; exit 1; }
if docker compose version >/dev/null 2>&1; then
  :
elif docker-compose version >/dev/null 2>&1; then
  :
else
  echo "❌ docker compose / docker-compose not found"; exit 1
fi
