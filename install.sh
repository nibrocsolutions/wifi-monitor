#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. On Raspberry Pi OS:"
  echo "  curl -fsSL https://get.docker.com | sh"
  echo "  sudo usermod -aG docker \$USER"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "Docker Compose is required (plugin or docker-compose)."
  exit 1
fi

"${compose[@]}" up -d --build

ip_addr="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "WiFi Monitor is running."
echo "Open http://${ip_addr:-127.0.0.1}:8085 from a browser on the same network."
