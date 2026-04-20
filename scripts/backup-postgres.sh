#!/usr/bin/env bash
# Nightly Postgres backup to Cloudflare R2. See docs/deployment/BACKUPS-AND-MEDIA.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

: "${DB_USER:=analytics_user}"
: "${DB_NAME:=analytics_db}"
: "${R2_BACKUP_REMOTE:=r2:versatex-backups/postgres}"
: "${BACKUP_RETENTION_DAYS:=30}"

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP_FILE="/tmp/postgres-${TIMESTAMP}.sql.gz"

docker compose exec -T db pg_dump \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --no-owner --no-acl \
  | gzip > "${DUMP_FILE}"

rclone copy "${DUMP_FILE}" "${R2_BACKUP_REMOTE}/"
rclone delete --min-age "${BACKUP_RETENTION_DAYS}d" "${R2_BACKUP_REMOTE}/"

rm -f "${DUMP_FILE}"

echo "Postgres backup complete: $(basename "${DUMP_FILE}")"
