#!/usr/bin/env bash
# Capacity watchdog. Alerts on:
#   - root disk usage > DISK_ALERT_PERCENT
#   - any docker container mem usage > MEMORY_ALERT_PERCENT of its limit
#   - Postgres DB size > DB_SIZE_ALERT_BYTES
#
# Scheduled every 15 minutes via cron. Exits 0 = OK, 1 = alerts fired.
# Posts the alert summary to ALERT_WEBHOOK_URL (ntfy / Slack) when present.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

: "${DB_USER:=analytics_user}"
: "${DB_NAME:=analytics_db}"
: "${DISK_ALERT_PERCENT:=80}"
: "${MEMORY_ALERT_PERCENT:=85}"
: "${DB_SIZE_ALERT_BYTES:=10737418240}"   # 10 GB
: "${ALERT_WEBHOOK_URL:=}"

problems=()

# 1. Root disk usage.
disk_pct=$(df / --output=pcent | tail -n 1 | tr -dc '0-9')
if [ -n "${disk_pct}" ] && [ "${disk_pct}" -gt "${DISK_ALERT_PERCENT}" ]; then
  problems+=("disk / at ${disk_pct}% (threshold ${DISK_ALERT_PERCENT}%)")
fi

# 2. Container memory (docker stats, point-in-time snapshot).
#    MemPerc is a string like "12.34%"; strip to integer for comparison.
while read -r name mem_pct_raw; do
  pct=$(echo "${mem_pct_raw}" | tr -dc '0-9.')
  [ -z "${pct}" ] && continue
  pct_int=${pct%.*}
  if [ "${pct_int:-0}" -gt "${MEMORY_ALERT_PERCENT}" ]; then
    problems+=("container ${name} mem at ${mem_pct_raw} (threshold ${MEMORY_ALERT_PERCENT}%)")
  fi
done < <(docker stats --no-stream --format '{{.Name}} {{.MemPerc}}')

# 3. Postgres DB size.
db_bytes=$(
  docker compose exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -tA \
    -c "SELECT pg_database_size(current_database())" 2>/dev/null \
  | tr -dc '0-9' \
  || echo 0
)
if [ -n "${db_bytes}" ] && [ "${db_bytes:-0}" -gt "${DB_SIZE_ALERT_BYTES}" ]; then
  db_gb=$(awk "BEGIN {printf \"%.2f\", ${db_bytes}/1073741824}")
  threshold_gb=$(awk "BEGIN {printf \"%.2f\", ${DB_SIZE_ALERT_BYTES}/1073741824}")
  problems+=("postgres DB size ${db_gb}GB (threshold ${threshold_gb}GB)")
fi

if [ "${#problems[@]}" -eq 0 ]; then
  db_mb=$(( ${db_bytes:-0} / 1048576 ))
  echo "OK: disk ${disk_pct}%, containers < ${MEMORY_ALERT_PERCENT}%, DB ${db_mb}MB"
  exit 0
fi

joined=$'Capacity alerts:\n'
for p in "${problems[@]}"; do
  joined+="- ${p}"$'\n'
done

printf '%s' "${joined}"

if [ -n "${ALERT_WEBHOOK_URL}" ]; then
  curl -sS -m 10 \
    -d "${joined}" \
    -H 'Title: Versatex capacity alert' \
    -H 'Tags: warning,bar_chart' \
    "${ALERT_WEBHOOK_URL}" > /dev/null || true
fi

exit 1
