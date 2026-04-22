#!/usr/bin/env bash
# Take a pre-deploy Postgres snapshot, tagged with the current git SHA.
# Called from the deploy playbook BEFORE running migrations so rollback has
# a recent restore point regardless of the nightly backup's staleness.
#
# Distinct from backup-postgres.sh by filename prefix + retention policy:
#   postgres-*.sql.gz       -> 30d retention (nightly schedule)
#   predeploy-*.sql.gz      -> 7d retention (deploy-time; short-lived by design)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

: "${DB_USER:=analytics_user}"
: "${DB_NAME:=analytics_db}"
: "${R2_BACKUP_REMOTE:=r2:versatex-backups/postgres}"
: "${PREDEPLOY_RETENTION_DAYS:=7}"

SHA=$(git rev-parse --short=12 HEAD)
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP_FILE="/tmp/predeploy-${SHA}-${TIMESTAMP}.sql.gz"

docker compose exec -T db pg_dump \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --no-owner --no-acl \
  | gzip > "${DUMP_FILE}"

rclone copy "${DUMP_FILE}" "${R2_BACKUP_REMOTE}/"

# Prune only predeploy-* files — never touch nightly postgres-*.sql.gz objects
# that share the same remote prefix.
rclone delete \
  --min-age "${PREDEPLOY_RETENTION_DAYS}d" \
  --include 'predeploy-*.sql.gz' \
  "${R2_BACKUP_REMOTE}/"

rm -f "${DUMP_FILE}"

echo "Predeploy snapshot complete: $(basename "${DUMP_FILE}")"
