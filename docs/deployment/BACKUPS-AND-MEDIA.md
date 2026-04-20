# Backups and Media Files

A single-VPS deployment has no automatic backups. This doc covers:

1. **Postgres logical backups** via `pg_dump` → Cloudflare R2.
2. **Media files** (org logos, generated PDF reports) persistence.
3. **Restore** procedure and drill cadence.

## Why R2

Cloudflare R2 is S3-compatible, offers 10 GB storage free, and charges **zero egress fees**. For backup workloads (write-heavy, read rare but urgent), R2 is strictly cheaper than S3.

## Postgres backups

### Create the R2 bucket

1. Cloudflare dashboard → **R2** → **Create bucket** → name: `versatex-backups` → location: Automatic.
2. **Manage R2 API Tokens** → **Create API Token**:
   - Permissions: **Object Read & Write**.
   - Specify bucket: `versatex-backups`.
   - TTL: (none, or rotate annually).
3. Copy the **Access Key ID** and **Secret Access Key** — shown once.
4. Note the **Account ID** from the R2 home page. The endpoint is `https://<account-id>.r2.cloudflarestorage.com`.

### Install rclone on the VPS

```bash
sudo apt update
sudo apt install -y rclone
rclone version
```

### Configure the R2 remote

Create `/home/deploy/.config/rclone/rclone.conf`:

```ini
[r2]
type = s3
provider = Cloudflare
access_key_id = <R2-access-key-id>
secret_access_key = <R2-secret-access-key>
endpoint = https://<account-id>.r2.cloudflarestorage.com
acl = private
```

Lock permissions:

```bash
chmod 600 ~/.config/rclone/rclone.conf
```

Test:

```bash
rclone mkdir r2:versatex-backups/postgres
rclone ls r2:versatex-backups
```

### Backup script

Create `scripts/backup-postgres.sh` in the repo:

```bash
#!/usr/bin/env bash
set -euo pipefail

cd /home/deploy/versatex-analytics

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
DUMP_FILE="/tmp/postgres-${TIMESTAMP}.sql.gz"

docker compose exec -T db pg_dump \
  -U "${DB_USER:-analytics_user}" \
  -d "${DB_NAME:-analytics_db}" \
  --no-owner --no-acl \
  | gzip > "${DUMP_FILE}"

rclone copy "${DUMP_FILE}" "r2:versatex-backups/postgres/"

# Retention: prune dumps older than 30 days
rclone delete --min-age 30d "r2:versatex-backups/postgres/"

rm -f "${DUMP_FILE}"

echo "Backup complete: ${DUMP_FILE}"
```

Make executable:

```bash
chmod +x scripts/backup-postgres.sh
```

### Schedule via cron

```bash
crontab -e
```

Add:

```cron
# Postgres backup to R2 daily at 03:00 UTC
0 3 * * * cd /home/deploy/versatex-analytics && set -a && . ./.env && set +a && ./scripts/backup-postgres.sh >> /var/log/pg-backup.log 2>&1
```

`set -a` / `. ./.env` / `set +a` exports variables from `.env` into the cron shell so the script can read `DB_USER` and `DB_NAME`.

Run once manually to confirm:

```bash
cd /home/deploy/versatex-analytics
set -a; . ./.env; set +a
./scripts/backup-postgres.sh

rclone ls r2:versatex-backups/postgres/
```

## Media files

`docker-compose.yml` declares a named volume `media_volume` for Django media (org logos in the `Organization.logo` field, generated PDF reports from `apps/reports`). Two strategies:

### Option A — Persist volume, sync to R2

Lower effort. The volume lives at `/var/lib/docker/volumes/<project>_media_volume/_data` on the host. Sync to R2 nightly.

Create `scripts/backup-media.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

VOLUME_PATH=$(docker volume inspect -f '{{ .Mountpoint }}' versatex-analytics_media_volume)

rclone sync "${VOLUME_PATH}" r2:versatex-backups/media --progress
```

Cron:

```cron
30 3 * * * /home/deploy/versatex-analytics/scripts/backup-media.sh >> /var/log/media-backup.log 2>&1
```

Downside: if the VPS disk dies between syncs, up to 24 hours of media is lost.

### Option B — Django writes to R2 directly (recommended for scale)

Use `django-storages[s3]` so media files go straight to R2. Zero sync lag; the VPS disk holds nothing you can't re-pull.

Add to `backend/requirements.txt`:

```
django-storages[s3]
```

Add to `backend/config/settings.py`:

```python
if os.getenv("USE_R2_MEDIA", "False").lower() == "true":
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": os.getenv("R2_MEDIA_BUCKET", "versatex-media"),
                "endpoint_url": os.getenv("R2_ENDPOINT"),
                "access_key": os.getenv("R2_ACCESS_KEY_ID"),
                "secret_key": os.getenv("R2_SECRET_ACCESS_KEY"),
                "region_name": "auto",
                "default_acl": "private",
                "querystring_auth": True,
                "querystring_expire": 3600,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
```

Env vars:

```env
USE_R2_MEDIA=True
R2_MEDIA_BUCKET=versatex-media
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<key>
R2_SECRET_ACCESS_KEY=<secret>
```

Create the `versatex-media` bucket in R2, separate from the backup bucket. Scope the API token to this bucket only.

Option B is the right call if users upload large files or the Reports module generates many PDFs.

## Restore procedure

### Postgres

```bash
# 1. Download the dump
rclone copy r2:versatex-backups/postgres/postgres-<timestamp>.sql.gz /tmp/

# 2. Stop writers so they don't race the restore
docker compose stop backend celery

# 3. Drop and recreate the database
docker compose exec -T db psql -U analytics_user -d postgres <<SQL
DROP DATABASE IF EXISTS analytics_db;
CREATE DATABASE analytics_db OWNER analytics_user;
SQL

# 4. Restore
gunzip -c /tmp/postgres-<timestamp>.sql.gz | \
  docker compose exec -T db psql -U analytics_user -d analytics_db

# 5. Restart services
docker compose start backend celery
```

Verify by logging in and checking recent transactions / insights match the timestamp you restored from.

### Media — Option A (volume sync)

```bash
VOLUME_PATH=$(docker volume inspect -f '{{ .Mountpoint }}' versatex-analytics_media_volume)
rclone sync r2:versatex-backups/media "${VOLUME_PATH}" --progress
```

### Media — Option B (R2 storage backend)

Nothing to restore — R2 is the source of truth.

## Drill cadence

Untested backups don't exist. Run a restore drill:

- **Monthly**: download the latest dump to a scratch VM, restore, verify row counts on key tables (`authentication_user`, `procurement_transaction`, `analytics_llmrequestlog`).
- **After any migration that changes schema significantly**: dry-run a restore + migrate.

Put it on the team calendar.

## Cost

| Workload | Typical monthly volume | R2 cost |
|----------|------------------------|---------|
| 30 daily Postgres dumps (~500 MB compressed each, 30-day retention) | ~15 GB | First 10 GB free; ~$0.08/mo after that ($0.015/GB) |
| Media files | ~5 GB | $0 (under free tier) |
| Egress during restore drills | ~10 GB | $0 — R2 has no egress fees |

Expect $0-$0.50/mo unless the database grows substantially.

## Links

- rclone S3 / R2 docs — https://rclone.org/s3/#cloudflare-r2
- django-storages S3 backend — https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
- Cloudflare R2 pricing — https://developers.cloudflare.com/r2/pricing/
