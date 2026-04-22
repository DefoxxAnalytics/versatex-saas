# Deploy Playbook

Runbooks for the Cloudflare Tunnel + Hetzner CX32 deployment defined in
[PRODUCTION-DEPLOY-PLAN.md](PRODUCTION-DEPLOY-PLAN.md). If you are reading
this, you are about to:

- ship a PR to production, or
- roll back a prod deploy, or
- run a migration on a live database, or
- rotate a secret.

Each section is self-contained. Read top-to-bottom the first time; skim
thereafter.

---

## 1. Pre-deploy checklist

Complete **all five** before touching the VPS.

| # | Check | Command / URL |
|---|---|---|
| 1 | CI green on `main` for the commit you want to deploy | GitHub → Actions → filter to main → expect green |
| 2 | GHCR build-push job for that commit completed | GitHub → Actions → "Deploy" workflow run for the sha → "Build & Push Docker Images" job green; images visible at `ghcr.io/defoxxanalytics/versatex-saas-backend:<sha>` and `...-frontend:<sha>` |
| 3 | You have the target `APP_VERSION` string | Short 12-char sha is preferred: `git rev-parse --short=12 <commit>` |
| 4 | A recent Postgres backup exists | EITHER yesterday's nightly (verify: `rclone lsjson r2:versatex-backups/postgres/ \| jq '.[-1].ModTime'` is <24 h old) OR run `./scripts/predeploy-snapshot.sh` on the VPS now |
| 5 | You can reach the VPS | `ssh deploy@<vps-ip>` succeeds; `docker ps` works |

**Fail fast:** if any of 1–4 are red, do not proceed. Step 5 failing means
investigate network/SSH before anything else.

---

## 2. Deploy runbook

```bash
# 1. SSH to the VPS as the deploy user.
ssh deploy@<vps-ip>
cd versatex-saas

# 2. Pull the code for the target sha (you need the repo in sync for
#    docker-compose.*.yml, scripts/, and nginx.conf which are bind-mounted).
git fetch origin
git checkout <APP_VERSION>

# 3. Take a predeploy snapshot — cheap insurance if migrations misbehave.
./scripts/predeploy-snapshot.sh
# Expected: "Predeploy snapshot complete: predeploy-<sha>-<ts>.sql.gz"

# 4. Pin the image and pull the new set.
export APP_VERSION=<sha>
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  -f docker-compose.monitoring.yml \
  pull

# 5. Up the stack (this is the actual swap).
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  -f docker-compose.monitoring.yml \
  up -d db redis backend celery flower frontend cloudflared uptime-kuma

# 6. Apply migrations.
docker compose exec backend python manage.py migrate

# 7. Collect static assets (only needed when admin assets change).
docker compose exec backend python manage.py collectstatic --noinput

# 8. Smoke check from the VPS.
curl -s http://localhost:8000/api/health/ | jq .
# Expected: {"db": "ok", "redis": "ok"}

# 9. Smoke check from the public URL.
curl -sI https://app.versatexanalytics.com/api/health/
# Expected: HTTP/2 200
```

Browser sanity (from your laptop, incognito to avoid cached sessions):
1. `https://app.versatexanalytics.com/` → login page renders.
2. Log in → dashboard loads, no CORS errors in DevTools Network tab.
3. `https://app.versatexanalytics.com/${ADMIN_URL}login/` → redirects to
   Cloudflare Access OTP challenge.
4. Verify Uptime Kuma (`https://monitor.versatexanalytics.com/`) shows all
   probes green.

**Declare "deploy green"** only after all nine steps + the 4 browser checks
pass.

---

## 3. Rollback runbook

Two paths, depending on whether the failing commit's migration was
forward-compatible (see §5 Migration safety).

### 3a. Image-only rollback (preferred; works when migrations are additive)

```bash
# Replace with the previous known-green sha.
export APP_VERSION=<prev-sha>
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  -f docker-compose.monitoring.yml \
  pull && \
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  -f docker-compose.monitoring.yml \
  up -d

# Verify.
curl -s https://app.versatexanalytics.com/api/health/ | jq .
```

Expected turnaround: **<90 seconds**. User sessions persist (Redis
`appendonly yes` keeps them across container restarts).

### 3b. Database restore rollback (only if 3a fails due to schema mismatch)

Happens when the failing release ran a migration that dropped or narrowed
a column the previous sha's code still reads. Full restore from the
predeploy snapshot taken in §2 step 3:

```bash
# 1. Stop app layers so they don't race the restore.
docker compose stop backend celery

# 2. Download the snapshot taken at the start of the failed deploy.
rclone copy \
  r2:versatex-backups/postgres/predeploy-<failed-sha>-<ts>.sql.gz \
  /tmp/

# 3. Drop + recreate the database.
docker compose exec -T db psql -U analytics_user -d postgres <<SQL
DROP DATABASE IF EXISTS analytics_db;
CREATE DATABASE analytics_db OWNER analytics_user;
SQL

# 4. Restore.
gunzip -c /tmp/predeploy-<failed-sha>-<ts>.sql.gz | \
  docker compose exec -T db psql -U analytics_user -d analytics_db

# 5. Now do the image rollback (§3a).
export APP_VERSION=<prev-sha>
docker compose ... pull && up -d
```

Expected turnaround: **~15 minutes** for a DB <5 GB. Verifies by
logging in → dashboard numbers match the pre-failed-deploy state.

**Full restore reference:** [BACKUPS-AND-MEDIA.md §Restore procedure](BACKUPS-AND-MEDIA.md#restore-procedure).

### 3c. Emergency: tunnel down but VPS alive

Cloudflare Tunnel has a regional outage. App becomes unreachable via
`app.versatexanalytics.com`. Short-term break-glass:

1. On the VPS: `sudo ufw allow 443/tcp` to open the port.
2. Update Cloudflare DNS: change the `app.*` record from the tunnel
   CNAME to a proxied A record pointing at the VPS IPv4.
3. Add a self-signed cert + run nginx with TLS (or keep Cloudflare
   "Full" mode with a cert on the VPS).
4. Once the tunnel is restored: revert DNS, close 443, restart
   `cloudflared`.

This path is documented here but not yet drilled. Schedule a drill when
bandwidth allows (P1 roadmap item in PRODUCTION-DEPLOY-PLAN.md).

---

## 4. Running migrations in prod

```bash
# 1. Pre-deploy snapshot (same as §2 step 3).
./scripts/predeploy-snapshot.sh

# 2. Apply.
docker compose exec backend python manage.py migrate

# 3. Verify the new schema version landed.
docker compose exec backend python manage.py showmigrations analytics | tail -5

# 4. Smoke any endpoint that uses the newly-changed table.
curl -s https://app.versatexanalytics.com/api/health/
```

If the migration adds an index on a large table, expect it to take
minutes. `SELECT 1` checks continue working during index creation
(Postgres doesn't lock the table for `CREATE INDEX CONCURRENTLY`; we don't
currently use CONCURRENTLY but should for indexes on tables >10K rows —
track as a future migration-helper improvement).

---

## 5. Migration safety rule

**Every migration must be forward-compatible for at least one rollback
cycle.** Concretely, a migration is safe to deploy if and only if:

| ✅ Safe (additive) | ❌ Unsafe until follow-up |
|---|---|
| Add a new column (nullable or with server default) | Drop a column |
| Add a new table | Drop a table |
| Add an index | Change a column type to a narrower type (e.g. `BigInt` → `Int`) |
| Expand an enum / choices | Add `NOT NULL` without `default` to an existing column |
| Rename a model's verbose label | Rename a column (Django's `rename` operation breaks old code) |

**Column removal procedure:**
1. Release N: stop reading the column in code; keep the column in the
   schema.
2. Release N+1: drop the column in a migration. By now, no deployed code
   reads it — rollback to release N still works because the schema's
   "dropped" column was already unused in N.

**Why this matters:** rollback via §3a only succeeds if the previous
release's code can run against the current schema. If release N+1 drops a
column that release N reads, rollback to N has no schema to read and the
app errors on every query.

**Drill proof:** Phase 13's rollback drill exercises one-release-back
rollback. Every release must therefore maintain compatibility with its
immediate predecessor.

---

## 6. Secret classification

Four tiers, defining how each secret is generated, rotated, and stored.

### Tier A — Generate once, never rotate unless leaked

Long-lived identifiers. Rotation requires a full reset (re-encrypt data or
regenerate every derived secret).

| Secret | Generator | Rotation trigger |
|---|---|---|
| `SECRET_KEY` | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` | Confirmed leak (git commit, public log) |
| `FIELD_ENCRYPTION_KEY` | `docker run --rm python:3.12-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | Confirmed leak. Rotation requires re-encrypting all affected field values (document pending in future P1 SECRET-ROTATION.md). |
| `ADMIN_URL` | `python -c "import secrets; print(f'manage-{secrets.token_hex(8)}/')"` | Enumeration observed in WAF logs / accidentally public |

### Tier B — Per-environment unique

Never share between dev/staging/prod. Rotate yearly or on staff turnover.

| Secret | Generator | Rotation trigger |
|---|---|---|
| `DB_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Staff turnover, confirmed leak, annual cadence |
| `REDIS_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Same |
| `FLOWER_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Same |

### Tier C — Third-party acquired

Obtained from an external service. Rotation follows the provider's own
runbook.

| Secret | Where from | Rotation trigger |
|---|---|---|
| `CLOUDFLARED_TOKEN` | Cloudflare Zero Trust → Tunnels → token copy-once | Tunnel recreated; tunnel compromise |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API keys | Unexpected usage spike; staff turnover |
| `OPENAI_API_KEY` | platform.openai.com → API keys | Same |
| `EMAIL_HOST_PASSWORD` | Resend dashboard → SMTP creds | Annual; sending-domain compromise |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | Cloudflare R2 → Manage R2 API Tokens | Annual; suspected leak |

### Tier D — Deploy-specific

Changes every deploy; not really a "secret" but belongs on the list.

| Variable | Source |
|---|---|
| `APP_VERSION` | Current git sha or release tag |
| `HSTS_INCLUDE_SUBDOMAINS` / `HSTS_PRELOAD` | Boolean; start `False`; flip after 1 week of prod stability |

### Storage policy

- `.env` file on VPS: `chmod 600`, owner `deploy`. Never readable by any
  other user.
- Encrypted copy in 1Password (or equivalent password manager). Updated
  on every rotation.
- Encrypted copy in R2 (so a VPS disk failure doesn't lock you out).
- Never commit `.env` to git. `.env.example` holds the keys + comments,
  never real values.

---

## 7. Prerequisite: GHCR image must exist before pull

`docker compose pull` will fail with
`manifest for ghcr.io/.../versatex-saas-backend:<sha> not found` if the
"Deploy" GitHub Actions workflow hasn't completed for that sha. Check:

```bash
gh run list --workflow=Deploy --branch=main --limit 5
```

Expect a green run for the target sha with "Build & Push Docker Images"
done. If it's still running (~3–5 min typical), wait. If it failed, the
deploy can't proceed — fix the failing job first.

See [.github/workflows/deploy.yml](../../.github/workflows/deploy.yml)
for the build logic. Every push to `main` triggers a build. Tags like
`v1.2.3` also trigger.

---

## 8. Common failure modes — 2-minute diagnoses

### "Infinite redirect loop on login"

**Symptom:** browser keeps bouncing between HTTP and HTTPS on any URL.

**Cause:** `SECURE_SSL_REDIRECT=True` (prod default) combined with
missing or broken `X-Forwarded-Proto` header propagation.

**Diagnosis:**
```bash
# From the VPS:
docker compose exec frontend cat /etc/nginx/conf.d/default.conf | grep -A 1 'map $http_x_forwarded_proto'
# Expect: map block present (pairs with settings.py's SECURE_PROXY_SSL_HEADER).
```

**Fix:** if the `map` block is absent, the nginx.conf bind mount is
stale or a bad image was deployed. Re-pull the target `APP_VERSION` or
roll back per §3a.

### "Admin page 404s"

**Symptom:** `curl -I https://app.versatexanalytics.com/admin/` returns
404.

**Cause:** `ADMIN_URL` is set to an obscured path (e.g.
`manage-abc123/`), so the literal `/admin/` is never routed to Django.

**Diagnosis:**
```bash
docker compose exec backend env | grep ADMIN_URL
```

**Fix:** use the configured path: `/manage-<hex>/login/`. Tell
teammates the URL out-of-band (1Password, not Slack).

### "R2 uploads fail with 403"

**Symptom:** new uploads throw `AccessDenied` in Django logs.

**Cause:** R2 API token expired, was rotated, or lost the right bucket
scope.

**Diagnosis:**
```bash
rclone lsd r2: 2>&1 | head -5
# Expect: "versatex-backups" and "versatex-media" listed.
```

**Fix:** regenerate the token in Cloudflare → R2 → Manage R2 API Tokens,
scoped to `versatex-media` with Object Read & Write. Update the `.env`
`R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`. Restart backend.

### "Cloudflare Access shows 'application not configured'"

**Symptom:** `/${ADMIN_URL}login/` returns CF error page instead of the
email OTP screen.

**Cause:** Access application's path pattern doesn't match the current
`ADMIN_URL`.

**Fix:** Cloudflare → Zero Trust → Access → Applications → `Versatex
Admin` → edit → update Path to `<current-ADMIN_URL>*`.

### "Celery beat stopped firing"

**Symptom:** `docker compose logs celery | tail -50` no longer shows
`beat: Starting...` at the expected schedule times.

**Cause:** the celerybeat-schedule file (in `/var/run/celery-beat/`, a
tmpfs) was corrupted OR the container restarted and lost its in-memory
schedule state.

**Fix:** restart the celery service. Beat re-runs any tasks missed while
it was down (short window).

```bash
docker compose restart celery
docker compose logs -f celery | head -20
# Expect: "celery@... ready" + "beat: Starting..." lines
```

### "pgvector missing after fresh migrate"

**Symptom:** migrations apply but `\d analytics_semanticcache` shows no
`ivfflat` index; semantic-cache queries are slow.

**Cause:** the `vector` extension is not enabled on the DB.

**Diagnosis:**
```bash
docker compose exec db psql -U analytics_user -d analytics_db \
  -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Fix:** enable manually:
```bash
docker compose exec db psql -U analytics_user -d analytics_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose exec backend python manage.py migrate analytics
```

In CI this is handled by
[.github/workflows/ci.yml](../../.github/workflows/ci.yml)'s "Enable
pgvector extension" step. In prod, the `pgvector/pgvector:pg15` image's
`init-pgvector.sql` does it on first boot — if you swap out the Postgres
image later, port that init script too.

---

## Cross-references

- [PRODUCTION-DEPLOY-PLAN.md](PRODUCTION-DEPLOY-PLAN.md) — the one-time
  VPS provisioning + Cloudflare setup that this playbook assumes.
- [MONITORING.md](MONITORING.md) — which alerts should fire when
  something goes wrong.
- [CLOUDFLARE-EDGE.md](CLOUDFLARE-EDGE.md) — cache / WAF / rate-limit
  rules applied at the Cloudflare zone.
- [BACKUPS-AND-MEDIA.md](BACKUPS-AND-MEDIA.md) — Postgres + media backup
  + restore procedures referenced above.
- [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md) — tunnel setup reference,
  useful when §3c break-glass is needed.

## Scope caveats

- **Django 2FA** is not enforced in v1. Admin access is gated by
  Cloudflare Access (email OTP). Two-factor-auth inside Django is a P1
  roadmap item.
- **Secret rotation runbook** (a full SECRET-ROTATION.md) is deferred to
  P1. The table in §6 is the current canonical source.
