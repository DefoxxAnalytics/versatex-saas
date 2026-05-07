# Production Deployment Plan — `app.versatexanalytics.com` on Cloudflare + Hetzner

Status: **Plan — not yet executed.** Save point for the refined ultraplan from the 2026-04-21 session.

## Context

The user owns `versatexanalytics.com` on Cloudflare (apex serves an existing marketing site) and needs a **permanent, production-grade** home for Versatex Analytics reachable at a subdomain. The earlier `trycloudflare.com` quick-tunnel was scratch-space; laptop-hosting is unacceptable for prod (sleep/reboot = downtime).

The recent single-origin refactor (`frontend/nginx/nginx.conf` proxies `/api|/admin|/static|/media` to `backend:8000`; `VITE_API_URL=/api`) is a keeper — it enables a **one-subdomain** deployment, avoiding the CORS/Pages-build/two-subdomain complexity of the existing [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md) recipe.

**Outcome:** `https://app.versatexanalytics.com` serves SPA + API + admin from a Hetzner **CX32** VPS (see sizing note below) via a Cloudflare named tunnel. Apex marketing site untouched. Always-on, HTTPS-only, nightly backups to R2, monitored by self-hosted Uptime Kuma + an external probe, admin gated by Cloudflare Access (Django 2FA is a P1 roadmap item, not in v1), rollback by GHCR-tagged images.

Three parallel pressure-tests surfaced the following blockers that separate "deploys successfully" from "production grade" — all integrated below rather than deferred.

## Approach: one-subdomain adaptation of the Hetzner recipe

The existing [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md) is ~80% reusable. Deviations:

| | Existing doc | This plan |
|---|---|---|
| Frontend | Cloudflare Pages static build | **Run the `frontend` Docker container** (its nginx proxies `/api`) |
| Tunnel target | `api.versatexanalytics.com` → `http://backend:8000` | `app.versatexanalytics.com` → `http://frontend:80` |
| Subdomains | `app.*` + `api.*` | `app.*` only |
| `VITE_API_URL` | baked `https://api.versatexanalytics.com/api` | `/api` (relative, already set) |
| VPS | CX22 suggested | **CX32 (8 GB)** — see sizing |
| Images | `build:` every deploy | `image:` pulled from GHCR (rollback-able) |
| Services up | `db redis backend celery flower cloudflared` | `db redis backend celery flower frontend cloudflared uptime-kuma` |

**VPS sizing — start at CX32, not CX22.** Capacity math (appendix) shows CX22's 4 GB leaves only ~1 GB headroom at idle and goes negative when nightly batch jobs + backup + autovacuum overlap. CX32 is €6.80/mo vs €4.51 (+€2.30) — cheap insurance against OOM-kills. Upgrade to CCX13 (dedicated vCPU, €13) before first paying customer.

## Files to modify

| Purpose | File |
|---|---|
| Forward-scheme pass-through (4 blocks) | `frontend/nginx/nginx.conf` |
| Prod CSP hardening | `frontend/nginx/nginx.conf` |
| HTTPS-behind-proxy; HSTS env-gated; LLM keys | `backend/config/settings.py` |
| Connection pooling | `backend/config/settings.py` |
| Restart policies + log rotation + resources + beat volume + image pinning | `docker-compose.prod.yml` |
| Tunnel depends on frontend + pinned image + fail-fast token | `docker-compose.tunnel.yml` |
| Uptime Kuma service | `docker-compose.monitoring.yml` (new) |
| Celery beat schedule volume | `docker-compose.prod.yml` |
| Gunicorn gthread + connection tuning | `docker-compose.yml` (base command) |
| pgvector index migration (follow-up) | `backend/apps/analytics/migrations/0013_add_vector_indexes.py` (new) |
| LLM cost digest task | `backend/config/celery.py` + `backend/apps/analytics/tasks.py` |
| `/api/health/` that touches DB + Redis | `backend/apps/analytics/views.py` (or dedicated `health` app) + `config/urls.py` |
| Deploy + rollback + migration-safety playbook | `docs/deployment/DEPLOY-PLAYBOOK.md` (new) |
| Monitoring runbook | `docs/deployment/MONITORING.md` (new) |
| Edge (Cache Rules / WAF / Rate-Limit / SSL) | `docs/deployment/CLOUDFLARE-EDGE.md` (new) |
| Secret rotation runbook | `docs/operations/SECRET-ROTATION.md` (new) |
| Variant section | `docs/deployment/CLOUDFLARE-HETZNER.md` (append) |
| Pre-deploy snapshot | `scripts/predeploy-snapshot.sh` (new) |
| Backup freshness alert | `scripts/check-backup-freshness.sh` (new) |
| Disk + memory watchdog | `scripts/capacity-check.sh` (new) |
| LLM keys + HSTS toggles | `.env.example` additions |

Reused verbatim (no edits): `docker-compose.yml` base services (except gunicorn cmd), `scripts/backup-postgres.sh`, `scripts/backup-media.sh`, `docs/deployment/BACKUPS-AND-MEDIA.md`, `docs/deployment/CLOUDFLARE-DNS.md`, `docs/deployment/CLOUDFLARE-TUNNEL.md`, `frontend/Dockerfile`, the existing `.github/workflows/deploy.yml` (produces GHCR images for `image:` pinning).

## Required code/config changes

### 1. `frontend/nginx/nginx.conf`

**a.** At `server` scope add:
```nginx
map $http_x_forwarded_proto $proxy_x_forwarded_proto {
    default $scheme;
    ~.+     $http_x_forwarded_proto;
}
```
**b.** Replace `X-Forwarded-Proto $scheme` with `X-Forwarded-Proto $proxy_x_forwarded_proto` in all 4 proxy blocks. Without this the cloudflared→nginx plaintext hop wipes out Cloudflare's `X-Forwarded-Proto: https`, breaking Django `SECURE_SSL_REDIRECT` in prod.

**c.** ~~Tighten CSP `connect-src` for production — drop `http://localhost:8001`, `http://127.0.0.1:8001`, `https://*.railway.app`. Leave `'self'` only (all traffic is same-origin now).~~ **DONE in v3.1 Phase 0 (F-H4).** Production CSP now ships as `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'self';` — `script-src` `'unsafe-inline'` was also dropped (Manus IDE-runtime plugin gated to dev-only in `vite.config.ts`).

### 2. `backend/config/settings.py`

Inside `if not DEBUG:` block (line ~361) add:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

Replace existing HSTS block (lines 368-370) with env-gated variants — `includeSubDomains` pinning all `*.versatexanalytics.com` to HTTPS is irreversible for a year and affects future subdomains (`staging.`, `sandbox.`, etc.):

```python
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('HSTS_PRELOAD', default=False, cast=bool)
```

Start with both `False`; enable after 1 week of `max-age=300` validation, then bump.

Near `FIELD_ENCRYPTION_KEY` (line ~394) declare the LLM keys (currently referenced via `getattr(settings, ...)` in `backend/apps/analytics/{views.py, rag_service.py, semantic_cache.py, document_ingestion.py}` but **never defined** in settings — AI features silently fail):

```python
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
```

In `DATABASES['default']` (line ~104) enable persistent connections:

```python
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
DATABASES['default']['OPTIONS'] = {'connect_timeout': 10}
```

### 3. `docker-compose.yml` — gunicorn concurrency

Change `backend.command` to:

```
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --worker-class gthread --timeout 120
```

Same memory as 4 sync workers; ~2-3× I/O-bound concurrency for API calls. Zero code risk.

### 4. `docker-compose.prod.yml`

Add across the board:

**a.** `restart: unless-stopped` on every service. Base compose has no restart policies — VPS reboots leave the stack dead.

**b.** Log rotation via anchor:
```yaml
x-logging: &default-logging
  driver: json-file
  options:
    max-size: "10m"
    max-file: "5"
```
Apply to every service via `logging: *default-logging`. Caps log footprint at ~300 MB. Without this, 40 GB disk fills in ~6 months.

**c.** Pin images to GHCR tags (the existing `.github/workflows/deploy.yml` already publishes these):
```yaml
backend:
  image: ghcr.io/defoxxanalytics/versatex-saas-backend:${APP_VERSION:-latest}
celery:
  image: ghcr.io/defoxxanalytics/versatex-saas-backend:${APP_VERSION:-latest}
  command: celery -A config worker -B -l info --concurrency=2 -s /beat/celerybeat-schedule
  volumes:
    - celery_beat_data:/beat
frontend:
  image: ghcr.io/defoxxanalytics/versatex-saas-frontend:${APP_VERSION:-latest}
```
`volumes: celery_beat_data:` persists beat's last-run file — without it, restarting the celery container loses schedule state and re-fires LLM batch jobs (2× cost).

**d.** Switch backend healthcheck from obscured `/${ADMIN_URL}login/` (requires ADMIN_URL to be set at start — fragile) to the new `/api/health/` endpoint once §2 adds it.

### 5. `docker-compose.tunnel.yml`

```yaml
cloudflared:
  image: cloudflare/cloudflared:2024.11.1   # pin, not :latest
  environment:
    - TUNNEL_TOKEN=${CLOUDFLARED_TOKEN:?CLOUDFLARED_TOKEN must be set}
  depends_on:
    - frontend   # was: backend
```

### 6. `docker-compose.monitoring.yml` (new)

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: analytics-uptime
    restart: unless-stopped
    volumes:
      - uptime_kuma:/app/data
    ports:
      - "127.0.0.1:3001:3001"   # exposed only to CF tunnel sidecar, not public
volumes:
  uptime_kuma:
```

Add second public hostname `monitor.versatexanalytics.com` → `http://uptime-kuma:3001` in the same tunnel, gate with Cloudflare Access. Configure Kuma probes: `/health`, `/api/health/`, `/${ADMIN_URL}login/`, DB TCP, Redis TCP. Push alerts to ntfy.sh (free) + email.

Plus one **external** probe that doesn't depend on the tunnel (from a free Fly.io / BetterStack / Healthchecks.io hitting the public URL).

### 7. New pgvector index migration

**Critical architectural gap surfaced by the capacity review.** The v2.9 migrations add `VectorField(dimensions=1536)` columns on `SemanticCache` and `EmbeddedDocument` but never create an ANN index. Every lookup does a sequential scan. Fine at 100 docs, catastrophic at 20K (gunicorn timeout).

Create `backend/apps/analytics/migrations/0013_add_vector_indexes.py`:

```python
from django.db import migrations
from pgvector.django import IvfflatIndex

class Migration(migrations.Migration):
    dependencies = [('analytics', '0012_...')]
    operations = [
        migrations.AddIndex(
            model_name='embeddeddocument',
            index=IvfflatIndex(
                name='embedded_doc_vec_idx',
                fields=['content_embedding'],
                lists=100,
                opclasses=['vector_cosine_ops'],
            ),
        ),
        migrations.AddIndex(
            model_name='semanticcache',
            index=IvfflatIndex(
                name='semantic_cache_vec_idx',
                fields=['query_embedding'],
                lists=100,
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
```

### 8. `backend/config/celery.py` + LLM cost digest task

Add Beat schedule:
```python
'llm_cost_digest_daily': {
    'task': 'apps.analytics.tasks.send_llm_cost_digest',
    'schedule': crontab(hour=6, minute=0),
},
```
Task sums `LLMRequestLog.cost_usd` for yesterday and POSTs to `COST_ALERT_WEBHOOK_URL` (Slack/ntfy). Prevents silent runaway spend on nightly batch jobs.

### 9. `/api/health/` readiness endpoint

The current nginx `/health` (line 83) returns 200 unconditionally. Useless as readiness. Add a Django view that runs `connection.cursor().execute('SELECT 1')` + Redis `PING`; returns 503 on failure. Point Kuma + backend healthcheck at it.

### 10. New scripts

- `scripts/predeploy-snapshot.sh` — wraps `backup-postgres.sh` with prefix `predeploy-<sha>-`, retention 7d. Called by the deploy playbook before migrations.
- `scripts/check-backup-freshness.sh` — `rclone lsjson` the postgres prefix; alert if latest >26h old. Cron every 6h.
- `scripts/capacity-check.sh` — `df /` disk, `docker stats` memory, `pg_database_size` — alert at disk>80%, container>85% mem, DB>10 GB. Cron every 15 min.

## Apex-safety pre-flight (do BEFORE touching Cloudflare)

The marketing site on `versatexanalytics.com` shares a Cloudflare zone with the new `app.*` subdomain. A few settings are **zone-wide** — they can't be scoped per-hostname — so changing them for the app can regress the marketing site unless pre-flighted. Complete this checklist before §3 ("Create named tunnel") in the operational steps.

### A. Inventory the current apex state (baseline — screenshot or capture to a private note)

1. **DNS records** — `dig versatexanalytics.com ANY +noall +answer` and `dig versatexanalytics.com NS`. Also export the full zone from CF dashboard → DNS → Records. Confirm what A/AAAA/CNAME/TXT records exist today so any post-deploy diff is attributable.
2. **Marketing origin** — where does the apex actually serve from? Cloudflare Pages? External host (Vercel, Netlify, own VPS)? Note the origin hostname/IP. Needed for §C.
3. **Current zone SSL/TLS mode** — CF dashboard → SSL/TLS → Overview. Record the current setting (`Flexible` / `Full` / `Full (strict)`).
4. **Zone-level HSTS** — SSL/TLS → Edge Certificates → HTTP Strict Transport Security. Record on/off and `max-age` / `includeSubDomains` / `preload` state.
5. **Existing rules** — screenshot the full lists in: Rules → Page Rules, Rules → Configuration Rules, Rules → Cache Rules, Rules → Redirect Rules, Rules → Transform Rules, Workers Routes, Security → WAF → Custom Rules, Security → WAF → Rate-Limiting Rules, Security → Bots.
6. **Always Use HTTPS** — SSL/TLS → Edge Certificates → "Always Use HTTPS". Record on/off.

### B. Pre-flight verify these before changing zone-wide settings

1. **`Full (strict)` compatibility** — this plan requires it. Zone-wide.
   - If current mode is already `Full (strict)`: no change needed. Skip.
   - If current mode is `Full` or `Flexible`: verify marketing origin serves a **valid non-self-signed** TLS cert on 443 before switching. Test from outside CF:
     ```bash
     curl -Iv --resolve versatexanalytics.com:443:<origin-ip> https://versatexanalytics.com/
     # or if origin is on Pages / a known PaaS, the cert is automatic — safe to switch
     ```
     If the cert is self-signed or the origin only speaks HTTP, **do not switch** — fix origin TLS first, or keep the zone on `Full` (plan works, the tunnel leg has its own TLS either way).
2. **HSTS / includeSubDomains / preload** — plan defaults both to `False` in `.env`. Keep at zone level too. If zone-level HSTS is currently **on** with `includeSubDomains=true`, the marketing site is already pinned to HTTPS — the plan's concern is moot. If it's off, keep it off until `app.*` has been stable for ≥1 week.
3. **"Always Use HTTPS"** — if currently off and marketing intentionally serves HTTP somewhere (rare, but some legacy setups do this), flipping it on will break that path. If marketing is modern / Pages-based, turn it on safely.
4. **Bot Fight Mode / WAF Managed Ruleset** — plan recommends enabling both. Zone-wide. Generally net-positive, but if marketing has legitimate automation/crawlers you care about (SEO tools, partner integrations), test a 24h window after enabling. Any false-positives are rollbackable in seconds.

### C. Rule scoping template — every new rule MUST be host-scoped

All Cache Rules, Rate-Limiting Rules, and WAF custom rules this plan adds **must include** `(http.host eq "app.versatexanalytics.com")` AND-ed with the path condition. Example expression:

```
(http.host eq "app.versatexanalytics.com" and starts_with(http.request.uri.path, "/assets/"))
```

Rules without the host filter apply to both the marketing site and the app subdomain — this is the single most likely way to accidentally regress marketing. `docs/deployment/CLOUDFLARE-EDGE.md` (new) will contain the exact expressions; verify every rule includes the host clause before clicking Save.

### D. Post-deploy apex regression check

Immediately after the tunnel goes live (after operational step §8):

```bash
# Capture baseline before deploy (from step A inventory), then compare:
curl -sI https://versatexanalytics.com/ | diff - apex-baseline-headers.txt
```

Expected: zero relevant diff (Cloudflare may add a `cf-ray` per request; that's fine). In browser: load marketing homepage + one deep link, confirm nothing visually or functionally changed. If the marketing site has forms / newsletter signup / external analytics — exercise one end-to-end.

### E. Emergency rollback for apex-affecting changes

If marketing regresses after a zone-wide change:

| Change | Rollback |
|---|---|
| SSL/TLS mode → `Full (strict)` broke marketing | Revert to previous mode in CF dashboard; applies in <30 s |
| New Cache Rule hit marketing paths | Delete the rule or add the `http.host` clause |
| Bot Fight Mode caused false-positives | Security → Bots → toggle off |
| HSTS accidentally enabled with preload | Disable in Edge Certs; browsers will still honor cached `max-age` for the remainder — another reason to keep preload off |
| New DNS record collision | Delete the errant record; apex CNAME/A records are untouched by this plan so collision is unlikely |

---

## One-time operational steps (on VPS)

Follow [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md) §1–§4 verbatim (VPS provision, SSH hardening, Docker install, repo clone), then:

1. **`.env` from `.env.example`**, set:
   ```env
   DEBUG=False
   ALLOWED_HOSTS=app.versatexanalytics.com
   ADMIN_URL=manage-<hex>/
   CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com
   CSRF_TRUSTED_ORIGINS=https://app.versatexanalytics.com
   FRONTEND_URL=https://app.versatexanalytics.com
   VITE_API_URL=/api
   HSTS_INCLUDE_SUBDOMAINS=False   # flip after 1 week
   HSTS_PRELOAD=False
   APP_VERSION=<git-sha-or-tag>
   USE_R2_MEDIA=True                # enable R2 media from day one
   ANTHROPIC_API_KEY=...
   OPENAI_API_KEY=...
   COST_ALERT_WEBHOOK_URL=https://ntfy.sh/<your-topic>
   ```
   Plus SECRET_KEY, DB_PASSWORD, REDIS_PASSWORD, FIELD_ENCRYPTION_KEY, FLOWER_PASSWORD, CLOUDFLARED_TOKEN, email settings (§2 below). `chmod 600 .env`. Stash an encrypted copy in 1Password + in R2.

2. **Email delivery.** Resend or Brevo free tier: sign up, verify `versatexanalytics.com`, add SPF/DKIM/DMARC records in Cloudflare DNS. `.env`:
   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.resend.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=resend
   EMAIL_HOST_PASSWORD=re_...
   DEFAULT_FROM_EMAIL="Versatex Analytics <noreply@versatexanalytics.com>"
   SERVER_EMAIL=alerts@versatexanalytics.com
   ```

3. **Cloudflare — create named tunnel** `versatex-prod` in Zero Trust. Copy token to `.env` as `CLOUDFLARED_TOKEN`.

4. **Map public hostnames** in the tunnel's Public Hostnames tab:
   - `app.versatexanalytics.com` → `HTTP` → `frontend:80`
   - `monitor.versatexanalytics.com` → `HTTP` → `uptime-kuma:3001`

5. **Cloudflare Access policies** (Required, not optional):
   - Application `Versatex Admin`: domain `app.versatexanalytics.com`, path `<ADMIN_URL>*` → email OTP, allowed emails list. Include a backup email.
   - Application `Versatex Monitor`: domain `monitor.versatexanalytics.com` → same allow list.

6. **GHCR auth on the VPS.** `docker login ghcr.io` with a `read:packages` PAT. Store in `~/.docker/config.json` (mode 600).

7. **Apply Cloudflare edge rules** per `docs/deployment/CLOUDFLARE-EDGE.md`:
   - SSL/TLS mode = **Full (strict)** (tunnels are compatible).
   - Cache Rule: cache `/assets/*` and fingerprinted static extensions 1y at edge.
   - Cache Rule: bypass cache on `/`, `/index.html`, `/api/*`, `/admin/*`, `/media/*`.
   - WAF: enable Cloudflare Managed Ruleset + Bot Fight Mode (both free).
   - Rate limit: `/api/v1/auth/login/` + `<ADMIN_URL>login*` → 10/10min per IP, block.

8. **Bring up the stack** with prod + tunnel + monitoring overlays:
   ```bash
   export APP_VERSION=<git-sha>
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
     up -d db redis backend celery flower frontend cloudflared uptime-kuma
   ```

9. **Bootstrap:**
   ```bash
   docker compose exec backend python manage.py migrate
   # collectstatic is automatic since v3.1 (backend/entrypoint.sh runs it
   # on every container start). Manual run is a fallback only.
   docker compose exec backend python manage.py createsuperuser
   # Link UserProfile per CLOUDFLARE-HETZNER.md §7 heredoc
   ```

10. **Backups to R2:** create bucket `versatex-backups`, scoped API token, install `rclone`, configure remote `r2:`. Install cron jobs (nightly pg at 03:00, media at 03:30, freshness check every 6h, capacity check every 15m). Run a restore drill against a throwaway DB before declaring done — confirm RTO ≤1h, RPO ≤24h.

11. **Configure Uptime Kuma** at `https://monitor.versatexanalytics.com`: probes on `/health`, `/api/health/`, admin login, DB TCP, Redis TCP, Postgres size query, external probe from Healthchecks.io (free). Push target: ntfy.sh topic + email.

## Verification — all must pass before declaring done

**Transport**
- `curl -IL https://app.versatexanalytics.com/` → 200 + HSTS header.
- `curl -IL http://app.versatexanalytics.com/` → 301 to HTTPS (CF edge).
- TLS mode shows **Full (strict)** in CF dashboard.

**App layers**
- `curl -sI https://app.versatexanalytics.com/api/v1/auth/user/` → 401 (Django responded).
- `curl -IL https://app.versatexanalytics.com/${ADMIN_URL}login/` → 302 to CF Access OTP challenge.
- `curl -s https://app.versatexanalytics.com/api/health/ | jq .` → `{"db":"ok","redis":"ok"}`.
- Browser test: full login → dashboard → SSE AI chat streams → report download works.
- `docker compose exec backend python manage.py check --deploy` → no warnings.
- `docker compose exec backend python -c "from django.core.mail import send_mail; send_mail('test','b',None,['you@…'])"` → email lands.

**Container health / restart**
- `docker compose ps` — all `healthy`.
- `sudo reboot` — after reboot, stack comes up unattended and all probes green within 90 s.

**Monitoring**
- CF Zero Trust tunnel status = HEALTHY.
- Uptime Kuma dashboard — all probes green, push notification delivered to ntfy.
- External probe confirms public URL reachable.

**Backups**
- Manual `./scripts/backup-postgres.sh && ./scripts/backup-media.sh` → objects in R2.
- Restore drill — `gunzip | psql` into scratch DB, counts match.
- `./scripts/check-backup-freshness.sh` → clean exit.

**Rollback drill**
- `APP_VERSION=<prev-sha> docker compose pull && docker compose up -d` — previous images pulled from GHCR, app reverts in <90 s. Confirm user session cookies still valid.

**Scheduled tasks**
- Within 24 h: `docker compose logs celery | grep -E 'batch_generate_insights|cleanup_|llm_cost_digest|process_scheduled_reports|cleanup_expired_reports'` — beat firing.
- Within 1 h of deploy: at least one `process_scheduled_reports` line in celery logs (hourly schedule). Silent failure mode: scheduled reports created via the UI never run.
- LLM cost digest POSTs to webhook.

**Non-regression**
- Apex `versatexanalytics.com` marketing site unchanged.

## Post-MVP roadmap (NOT in v1 deploy — tracked for follow-up)

**P1 — within first week of going live:**
- `django-two-factor-auth` + `django-otp` in requirements, enforced on `is_staff` users (defense-in-depth beyond CF Access).
- `docs/operations/SECRET-ROTATION.md` — per-secret runbook (SECRET_KEY, DB, Redis, FIELD_ENCRYPTION_KEY, LLM keys).
- AuditLog mirror to stdout for external log retention.
- Grafana Cloud free tier + cAdvisor + postgres_exporter + redis_exporter as `docker-compose.monitoring.yml` overlay.
- Cloudflared break-glass doc (standby tunnel token in 1Password; UFW rule template).
- Per-org partial pgvector indexes once org count ≥10.

**P2 — post-MVP polish:**
- Log shipping to Grafana Loki or Better Stack (ship `audit` logs with 1y retention).
- Feature flags for backward-compat windows during deploys (new frontend shouldn't call new API before migration completes).
- `django-celery-beat` — DB-backed schedule, survives restarts natively, editable via admin (replaces file-based beat once multi-worker).
- Quarterly DR drill on throwaway CX11 — timed, documented.
- Monthly automated restore-test cron (not just manual drill).
- Switch gunicorn from sync to gthread tuned further based on `py-spy` profiling.
- Parallelize `batch_generate_insights` once org count >25 (currently serial in `tasks.py:354`).

## Capacity appendix

**CX32 is the entry-level floor, not the target.** Realistic RAM math (kernel + Docker + PG 600 MB + Redis 320 MB + gunicorn gthread 2×400 MB + celery 400 MB + flower 80 MB + cloudflared 40 MB + nginx 20 MB + uptime-kuma 100 MB) ≈ 2.8 GB steady, peaks to ~4 GB under concurrent batch + backup + autovacuum. CX32's 8 GB leaves comfortable headroom. CX22's 4 GB did not.

**Breakpoints:**

| Signal | Action |
|---|---|
| `docker stats` container >85% mem sustained 60 s | Upgrade CX32 → CCX13 (dedicated vCPU) |
| `dmesg \| grep -i "killed process"` non-empty | Upgrade immediately |
| pgvector sequential scan p50 >500 ms | Confirm `0013_add_vector_indexes.py` applied; raise `ivfflat.probes` |
| `batch_generate_insights` wall time >30 min | Add parallelism in `apps/analytics/tasks.py` |
| EmbeddedDocument count >20 K | Partial indexes per org |
| Disk >80 % | `capacity-check.sh` alerts; `docker image prune -a`, rotate backup retention |
| Concurrent users >25 sustained | Switch to CCX23 or extract Postgres to Crunchy Bridge / self-managed DB box |

**Vertical ceiling on single-box:** CCX33 (€50/mo, 32 GB, 8 dedicated vCPU). Beyond: extract DB (Crunchy Bridge / self-hosted 2nd box) + Celery worker onto a 2nd VPS.

## Risks & conscious tradeoffs

- **100 MB CF request body cap** — admin CSV import fails above it. Mitigation documented in existing [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md) §Admin panel: `scp` + `import_p2p_data` over SSH for large files.
- **Celery Beat embedded in worker** (with schedule volume) — worker OOM takes beat with it. Acceptable at one-VPS scale; split when adding 2nd worker (P2 moves to `django-celery-beat`).
- **Nightly-only backups** — RPO = 24h worst case, reduced to "last deploy OR last nightly" for prod-changing deploys via `predeploy-snapshot.sh`. Not PITR; accepted at this scale.
- **Single-VPS SPOF** — a 30 min–4 h Cloudflare or Hetzner incident takes the app down. Break-glass UFW rule documented (P1) but accepted — higher availability = multi-region, out of scope for MVP.
- **LLM key exposure surface** — keys live in `.env` on VPS. No external secrets manager. Rotation doc (P1) makes replacement a 5 min exercise if compromised.
- **`SECURE_SSL_REDIRECT=True` depends on `X-Forwarded-Proto`** flowing correctly through cloudflared → nginx → Django. The §1a `map` block is load-bearing; confirm in verification step.
- **CX32 not CX22** — +€2.30/mo over the doc's suggestion. Cheap insurance for production; downgrade later if metrics show persistent idle capacity.
