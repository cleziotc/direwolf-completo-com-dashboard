#!/usr/bin/env bash
set -Eeuo pipefail
RAW="https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/scripts/install-common.sh"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
if [[ -n "$HERE" && -f "$HERE/scripts/install-common.sh" ]]; then
  exec bash "$HERE/scripts/install-common.sh" ubuntu
fi
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
curl -fsSL "$RAW" -o "$TMP"
exec bash "$TMP" ubuntu
