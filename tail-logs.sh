#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-}"

cd "$(dirname "$0")"

if [[ -n "$SERVICE" ]]; then
  sudo docker compose logs -f --tail=200 "$SERVICE"
else
  sudo docker compose logs -f --tail=200
fi
