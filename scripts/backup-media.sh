#!/usr/bin/env bash
# Media volume -> R2 sync (Option A). See docs/deployment/BACKUPS-AND-MEDIA.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

: "${COMPOSE_PROJECT_NAME:=versatex-analytics}"
: "${R2_MEDIA_REMOTE:=r2:versatex-backups/media}"

VOLUME_NAME="${COMPOSE_PROJECT_NAME}_media_volume"
VOLUME_PATH=$(docker volume inspect -f '{{ .Mountpoint }}' "${VOLUME_NAME}")

rclone sync "${VOLUME_PATH}" "${R2_MEDIA_REMOTE}"

echo "Media sync complete from ${VOLUME_PATH}"
