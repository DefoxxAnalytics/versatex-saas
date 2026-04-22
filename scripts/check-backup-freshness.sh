#!/usr/bin/env bash
# Alert if the newest postgres-*.sql.gz backup in R2 is older than the
# configured max-age (default 26h — 2h grace after the 03:00 UTC nightly
# cron). Scheduled via cron every 6h.
#
# Exits 0 = backups healthy, 1 = stale, 2 = no backups found.
# Posts the failure message to ALERT_WEBHOOK_URL if set (ntfy / Slack / Teams).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

: "${R2_BACKUP_REMOTE:=r2:versatex-backups/postgres}"
: "${BACKUP_MAX_AGE_HOURS:=26}"
: "${ALERT_WEBHOOK_URL:=}"

# Newest object's modification time in epoch seconds.
# rclone lsjson emits an empty array when the prefix exists but is empty.
newest_epoch=$(
  rclone lsjson --include 'postgres-*.sql.gz' "${R2_BACKUP_REMOTE}/" \
    | python3 -c "
import json, sys
from datetime import datetime
entries = json.load(sys.stdin)
if not entries:
    print(0)
else:
    ts_list = [
        datetime.fromisoformat(e['ModTime'].replace('Z', '+00:00')).timestamp()
        for e in entries
    ]
    print(int(max(ts_list)))
"
)

now_epoch=$(date +%s)
age_hours=$(( (now_epoch - newest_epoch) / 3600 ))

if [ "${newest_epoch}" -eq 0 ]; then
  message="ERROR: no postgres-*.sql.gz backups found in ${R2_BACKUP_REMOTE}"
  exit_code=2
elif [ "${age_hours}" -gt "${BACKUP_MAX_AGE_HOURS}" ]; then
  message="ERROR: newest postgres backup is ${age_hours}h old (threshold: ${BACKUP_MAX_AGE_HOURS}h)"
  exit_code=1
else
  message="OK: newest postgres backup is ${age_hours}h old"
  exit_code=0
fi

echo "${message}"

if [ -n "${ALERT_WEBHOOK_URL}" ] && [ "${exit_code}" -ne 0 ]; then
  curl -sS -m 10 \
    -d "${message}" \
    -H 'Title: Versatex backup freshness alert' \
    -H 'Tags: warning,floppy_disk' \
    "${ALERT_WEBHOOK_URL}" > /dev/null || true
fi

exit ${exit_code}
