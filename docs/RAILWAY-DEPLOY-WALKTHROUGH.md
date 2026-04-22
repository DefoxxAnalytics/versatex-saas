# Railway First Deploy Walkthrough

Step-by-step walkthrough for deploying Versatex Analytics to
[Railway](https://railway.app). Picks up after `deploy/prep` has merged
to `main` and GHCR images are published.

Railway is the right choice when:
- You want zero VPS management (no SSH, no Docker install, no
  hardening).
- Managed Postgres + Redis + backups out of the box.
- $25–45/mo is within budget.

Every step is checkpointed — you can pause between any two steps
without losing state. Natural pause points marked 🛑.

## Architecture decision — two subdomains

Unlike the Hetzner plan (single-origin via Cloudflare Tunnel), the
Railway deploy uses **two subdomains**:

- `api.versatexanalytics.com` → `backend` service (Django)
- `app.versatexanalytics.com` → `frontend` service (nginx serving SPA)

Why: Railway gives each service its own domain and expects that pattern.
The single-origin proxy used in the Hetzner plan would need a custom
nginx entrypoint to interpolate Railway's internal hostnames, adding
complexity that defeats Railway's point. Two subdomains + CORS is the
clean fit.

The backend already supports CORS via `CORS_ALLOWED_ORIGINS` /
`CSRF_TRUSTED_ORIGINS` env vars — no code changes.

## Prerequisites

Check all of these before starting.

- [ ] **Railway account** (sign up at [railway.app](https://railway.app))
- [ ] **Payment method** on Railway (won't be charged until you exceed
      the Hobby plan's $5/mo credit)
- [ ] **GitHub account** with repo access (Railway pulls from GitHub
      directly; no manual Docker image builds)
- [ ] **Cloudflare account** managing `versatexanalytics.com` (already
      exists)
- [ ] **Password manager** open (you'll save ~8 credentials)
- [ ] **Phone with ntfy app** installed (for push alerts)
- [ ] **Local Git Bash / WSL** terminal (for Railway CLI)

**Time estimate:** ~2.5 hours end-to-end. Natural break points noted.

---

# PHASE 10R — Railway project + infrastructure (~30 min)

## 10R.1 — Install Railway CLI

Optional but recommended — makes migrations and `railway run` much
easier than the dashboard shell.

On your laptop (Git Bash / WSL):

```bash
npm install -g @railway/cli
railway --version
# Expected: railway X.X.X
```

Then log in:

```bash
railway login
# Opens browser; approve the CLI login; return to terminal
```

🛑 **Checkpoint 10R.1:** `railway --version` works, CLI is
authenticated.

## 10R.2 — Create Railway project

Browser:

1. Go to [railway.app/dashboard](https://railway.app/dashboard).
2. **+ New Project** → **Empty Project**.
3. Rename it: click the project name (top-left) → `Versatex
   Production`.
4. **Copy the Project ID** (in the URL:
   `railway.app/project/[PROJECT_ID]`) → save in 1Password.

🛑 **Checkpoint 10R.2:** Empty project created.

## 10R.3 — Add Postgres + Redis

Inside the project:

1. **+ New → Database → Add PostgreSQL**. Wait ~20 s for provisioning.
   - Click the service card → rename to `postgres`.
2. **+ New → Database → Add Redis**. Wait ~20 s.
   - Rename to `redis`.

Railway auto-populates these reference variables:
- `postgres` exposes `DATABASE_URL` (full `postgres://...` connection
  string)
- `redis` exposes `REDIS_URL`

We'll reference these later via `${{postgres.DATABASE_URL}}` /
`${{redis.REDIS_URL}}` syntax in other services' env vars.

🛑 **Checkpoint 10R.3:** Both databases running. Two service cards
visible (`postgres` + `redis`).

## 10R.4 — Enable pgvector extension

Postgres ships without `vector` enabled. Enable it manually:

1. Click the `postgres` service card → **Data** tab.
2. **Query** → run:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. Verify:

   ```sql
   SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
   ```

   Expected: one row with `vector`.

🛑 **Checkpoint 10R.4:** pgvector extension installed. Without this,
migration `0006_add_vector_indexes` would fail on the IVFFlat index
creation.

---

# PHASE 11R — Deploy services (~90 min)

## 11R.1 — Connect GitHub repo

Railway will pull directly from your GitHub repo. One-time setup:

1. In the Railway project, click **+ New → GitHub Repo**.
2. First-time: click **Configure GitHub App** → grant Railway access
   to `DefoxxAnalytics/versatex-saas` only. Install.
3. Select `DefoxxAnalytics/versatex-saas`.
4. Railway starts auto-deploy immediately — **click the ×** on the
   deployment to cancel it. We'll configure before letting it run.

🛑 **Checkpoint 11R.1:** Repo connected. One empty service card
visible (Railway named it something like `versatex-saas`).

## 11R.2 — Deploy the backend service

1. Click the new service card → rename to `backend`.
2. **Settings tab → Source**:
   - **Root Directory**: leave empty (repo root — Dockerfile
     discovery from there)
   - **Dockerfile Path**: `backend/Dockerfile`
3. **Settings tab → Build**:
   - **Builder**: Dockerfile
4. **Settings tab → Deploy**:
   - **Start Command**:
     ```
     python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class gthread --timeout 120
     ```
     Note: `$PORT` is Railway-provided (not our `.env`'s port). Running
     migrations on boot is acceptable for a single-instance deploy;
     switch to a separate migration job if you scale beyond 1 replica.
   - **Healthcheck Path**: `/api/health/`
   - **Healthcheck Timeout**: 100s
5. **Variables tab** → paste the following (each as a separate
   variable; use Raw Editor for bulk paste):

   ```env
   # Django
   DJANGO_SETTINGS_MODULE=config.settings
   DEBUG=False
   SECRET_KEY=<generate in 11R.3>
   ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}},api.versatexanalytics.com
   ADMIN_URL=<generate in 11R.3>
   FRONTEND_URL=https://app.versatexanalytics.com

   # Database (Railway reference variable)
   DATABASE_URL=${{postgres.DATABASE_URL}}

   # Redis (Railway reference variable)
   REDIS_URL=${{redis.REDIS_URL}}
   CELERY_BROKER_URL=${{redis.REDIS_URL}}
   CELERY_RESULT_BACKEND=${{redis.REDIS_URL}}

   # CORS / CSRF (allow the frontend subdomain to call this one)
   CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com
   CSRF_TRUSTED_ORIGINS=https://app.versatexanalytics.com

   # HTTPS enforcement
   SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
   HSTS_INCLUDE_SUBDOMAINS=False
   HSTS_PRELOAD=False

   # Field encryption
   FIELD_ENCRYPTION_KEY=<generate in 11R.3>

   # Email (Resend)
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.resend.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=resend
   EMAIL_HOST_PASSWORD=<Resend API key, from 11R.4>
   DEFAULT_FROM_EMAIL=Versatex Analytics <noreply@versatexanalytics.com>
   SERVER_EMAIL=alerts@versatexanalytics.com

   # R2 media storage (optional — see 11R.5)
   USE_R2_MEDIA=True
   R2_MEDIA_BUCKET=versatex-media
   R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
   R2_ACCESS_KEY_ID=<from 11R.5>
   R2_SECRET_ACCESS_KEY=<from 11R.5>

   # LLM keys (optional)
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=

   # Cost digest webhook (optional)
   COST_ALERT_WEBHOOK_URL=
   ```

   We'll fill the `<generate in...>` placeholders in 11R.3–11R.5 before
   triggering the first deploy.

6. **Settings tab → Networking → Generate Domain**. Railway assigns
   a `*.up.railway.app` URL (e.g.
   `backend-production-abc.up.railway.app`). Copy this — you'll need
   it for the frontend's `VITE_API_URL` at least until you set up a
   custom domain.

🛑 **Checkpoint 11R.2:** Backend service configured. `*.up.railway.app`
domain generated. Do NOT deploy yet.

## 11R.3 — Generate secrets

On your laptop (Git Bash / WSL — no VPS involved anymore):

```bash
# SECRET_KEY
python -c "from secrets import choice; import string; print(''.join(choice(string.ascii_letters + string.digits + '!@#$%^&*(-_=+)') for _ in range(50)))"
# Save → 1Password "Versatex Railway SECRET_KEY"

# FIELD_ENCRYPTION_KEY (must be Fernet — needs cryptography package)
pip install cryptography --quiet 2>/dev/null
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Save → "Versatex Railway FIELD_ENCRYPTION_KEY"

# ADMIN_URL
python -c "import secrets; print(f'manage-{secrets.token_hex(8)}/')"
# Save → "Versatex Railway ADMIN_URL"
```

Paste each into the backend service's Variables tab in Railway.

🛑 **Checkpoint 11R.3:** Three secrets generated and pasted into
Railway backend variables.

## 11R.4 — Resend domain + API key

Same as Hetzner walkthrough Phase 11.4 — Resend is platform-agnostic.

1. [resend.com](https://resend.com) → sign up.
2. **Domains → Add Domain** → `versatexanalytics.com` → Add.
3. Copy the 3 DNS records shown (SPF, DKIM, DMARC).
4. Cloudflare dashboard → `versatexanalytics.com` → DNS → add the 3
   records. **Proxy status: DNS only (grey cloud)** for all three.
5. Back in Resend → **Verify DNS Records**.
6. **API Keys → Create API key** → scope: Sending access, domain:
   `versatexanalytics.com` → Copy key (starts with `re_`).
7. Paste into Railway backend's `EMAIL_HOST_PASSWORD`.

🛑 **Checkpoint 11R.4:** Resend verified. API key pasted.

## 11R.5 — R2 buckets (optional but recommended)

Managed Postgres includes backups so you don't strictly need R2 for
DB dumps, but media uploads still need somewhere. Options:

**Option A — R2 for media (recommended):** follow Hetzner walkthrough
Phase 11.3 to create `versatex-media` bucket + API token. Paste 3
values (endpoint, access key, secret) into Railway backend vars. Skip
the `versatex-backups` bucket — Railway Postgres has daily backups
built-in.

**Option B — Railway volume for media:** Railway offers persistent
volumes ($0.25/GB-month). Mount one at `/app/media`. Set
`USE_R2_MEDIA=False` in backend variables. Simpler, slightly more
expensive over time. Not recommended — volumes aren't backed up as
reliably as R2.

Choose one. Paste results into Railway variables.

🛑 **Checkpoint 11R.5:** Media storage chosen and configured.

## 11R.6 — Deploy the celery worker

1. **+ New → GitHub Repo** → select the same repo → cancel auto-deploy.
2. Rename the service to `celery`.
3. **Settings → Source → Dockerfile Path**: `backend/Dockerfile` (same
   Dockerfile, different start command).
4. **Settings → Deploy → Start Command**:
   ```
   celery -A config worker -B -l info --concurrency=2 -s /tmp/celerybeat-schedule
   ```
   The `-B` embeds Beat in the worker; `/tmp` is writable. Single-
   instance scale: fine; split to dedicated `celery-beat` service when
   adding a second worker.
5. **Settings → Networking → Remove Public Domain**. Celery doesn't
   need a public URL. (If Railway auto-generated one, delete it.)
6. **Variables tab → Add All Variables from → backend**. This copies
   the backend's env. Then **remove** these (celery doesn't need them):
   - `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`,
     `SECURE_PROXY_SSL_HEADER`, `HSTS_*`, `FRONTEND_URL`

🛑 **Checkpoint 11R.6:** Celery service configured, no public domain,
env vars copied from backend minus HTTP-specific ones.

## 11R.7 — Deploy the frontend service

1. **+ New → GitHub Repo** → select same repo → cancel auto-deploy.
2. Rename to `frontend`.
3. **Settings → Source → Dockerfile Path**: `frontend/Dockerfile`.
4. **Settings → Build → Build Arguments**:
   ```
   VITE_API_URL=https://<backend-railway-subdomain>.up.railway.app/api
   VITE_APP_TITLE=Versatex Analytics
   VITE_APP_LOGO=/vtx_logo2.png
   ```
   Replace `<backend-railway-subdomain>` with the backend's domain from
   11R.2 (e.g. `https://backend-production-abc.up.railway.app/api`). We
   swap this for `https://api.versatexanalytics.com/api` once the
   custom domain is live in Phase 12R.
5. **Settings → Networking → Generate Domain**.
6. **Variables tab**: no secrets needed (SPA is static; all config is
   baked at build time via the build args above).

🛑 **Checkpoint 11R.7:** Frontend service configured.

## 11R.8 — Deploy everything

You've configured 3 services; now deploy them in order (backend first
because it runs migrations on boot; celery + frontend need the DB
ready).

1. **backend** service → **Deployments** tab → **Deploy**. Watch logs.
   Expected stages:
   - "Building" (3–5 min — Docker image build)
   - "Deploying" (30 s)
   - "Active" with a green dot + `/api/health/` healthcheck passing
   - Migrations apply on boot — check logs for
     `Applying analytics.0006_add_vector_indexes... OK`.
2. **celery** → Deploy. Watch logs for
   `celery@... ready` + `beat: Starting...`.
3. **frontend** → Deploy. Watch logs for
   `nginx: configuration file ... test is successful` + healthcheck
   green.

🛑 **Checkpoint 11R.8:** All 5 services green (backend, celery,
frontend, postgres, redis).

## 11R.9 — Create superuser

```bash
# In your laptop's terminal, linked to the Railway project
cd <anywhere>
railway link
# Select the "Versatex Production" project

railway run -s backend python manage.py createsuperuser
# Prompts for username/email/password. Save in 1Password.

# Link UserProfile
railway run -s backend python manage.py shell <<'PY'
from apps.authentication.models import Organization, UserProfile
from django.contrib.auth import get_user_model
User = get_user_model()
org, _ = Organization.objects.get_or_create(slug="default", defaults={"name": "Default Organization"})
admin = User.objects.filter(is_superuser=True).order_by("id").first()
if admin is None:
    raise SystemExit("No superuser found")
profile, _ = UserProfile.objects.get_or_create(
    user=admin,
    defaults={"organization": org, "role": "admin", "is_active": True},
)
if profile.organization != org:
    profile.organization = org
    profile.role = "admin"
    profile.is_active = True
    profile.save()
print(f"Linked {admin.username} to {org.name} (role={profile.role})")
PY
```

🛑 **Checkpoint 11R.9:** Superuser created and linked.

## 11R.10 — Smoke test (pre-custom-domain)

From your laptop:

```bash
# Replace <backend-domain> and <frontend-domain> with the Railway-generated URLs
curl -s https://<backend-domain>.up.railway.app/api/health/ | jq .
# Expected: {"db": "ok", "redis": "ok"}

curl -sI https://<backend-domain>.up.railway.app/api/v1/auth/user/
# Expected: HTTP/2 401 (Django responded, not authed)
```

Browser:

1. Open `https://<frontend-domain>.up.railway.app/` → login page
2. **Expected CORS error** on login attempt until you do this: in the
   Railway `backend` service's variables, **temporarily add** the
   frontend's `*.up.railway.app` domain to `CORS_ALLOWED_ORIGINS` and
   `CSRF_TRUSTED_ORIGINS` so you can log in with the placeholder
   subdomains before the custom domain is live:
   ```
   CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com,https://<frontend-domain>.up.railway.app
   CSRF_TRUSTED_ORIGINS=https://app.versatexanalytics.com,https://<frontend-domain>.up.railway.app
   ```
   Redeploy backend (auto-redeploys on var change).
3. Log in with superuser → dashboard loads.

🛑 **Checkpoint 11R.10:** Login works against Railway-generated URLs.
**Phase 11R complete.** Good natural break point.

---

# PHASE 12R — Custom domains + Cloudflare (~45 min)

## 12R.1 — Add custom domains in Railway

For each of `backend` and `frontend`:

1. Service → **Settings → Networking → Custom Domain**.
2. **backend**: add `api.versatexanalytics.com`
3. **frontend**: add `app.versatexanalytics.com`
4. Railway shows a CNAME target for each (e.g.
   `<randomstring>.up.railway.app`). Copy both.

## 12R.2 — Cloudflare DNS records

Cloudflare dashboard → `versatexanalytics.com` → **DNS → Records**:

- **Add record**:
  - Type: `CNAME`
  - Name: `api`
  - Target: the backend's Railway CNAME from 12R.1
  - Proxy status: **DNS only (grey cloud)** initially — switch to
    proxied after verifying it works
  - TTL: Auto
- **Add record**:
  - Type: `CNAME`
  - Name: `app`
  - Target: the frontend's Railway CNAME from 12R.1
  - Proxy status: DNS only initially
  - TTL: Auto

Wait ~60 s for DNS propagation + Railway TLS provisioning.

## 12R.3 — Verify custom domains

```bash
curl -IL https://api.versatexanalytics.com/api/health/
# Expected: HTTP/2 200 with body {"db":"ok","redis":"ok"}

curl -IL https://app.versatexanalytics.com/
# Expected: HTTP/2 200
```

If either returns SSL errors, wait another minute — Railway issues the
cert on first request.

## 12R.4 — Update CORS + frontend build arg

In Railway `backend` variables:

```
CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com
CSRF_TRUSTED_ORIGINS=https://app.versatexanalytics.com
ALLOWED_HOSTS=api.versatexanalytics.com
```

(Drop the `*.up.railway.app` entries — custom domains are canonical
now.)

In Railway `frontend` build arguments:

```
VITE_API_URL=https://api.versatexanalytics.com/api
```

Trigger rebuild on both services (Deployments tab → **Redeploy**).
Frontend needs a fresh build because `VITE_API_URL` is baked at
build time.

## 12R.5 — Enable Cloudflare proxy (optional — adds WAF + cache)

Once custom domains work end-to-end with "DNS only" orange cloud off:

1. Cloudflare DNS → click the `api` CNAME → **Edit** → Proxy status:
   **Proxied (orange cloud)** → Save.
2. Same for `app`.
3. **SSL/TLS → Overview** → set zone to **Full (strict)** (Railway's
   cert is valid, so this works).

After proxy enabled, follow [deployment/CLOUDFLARE-EDGE.md](deployment/CLOUDFLARE-EDGE.md)
to apply cache + rate-limit rules — they're platform-agnostic and
benefit Railway equally. Adapt the `http.host` expressions to include
BOTH `app.versatexanalytics.com` AND `api.versatexanalytics.com`
(separate rules per subdomain).

## 12R.6 — Cloudflare Access (optional — gate admin)

Same as Hetzner walkthrough Phase 11.2 — Cloudflare Access is
deploy-target-agnostic. Gate `api.versatexanalytics.com/<ADMIN_URL>*`
behind email OTP.

🛑 **Checkpoint 12R:** Custom domains live. Cloudflare proxy +
Access optional layers active. **Phase 12R complete.**

---

# What's next

Round D (verification + post-deploy watch) mirrors the Hetzner plan:

- **Phase 13R — Verification.** Same curl checks against the custom
  domain, browser smoke, migration rollback drill via `railway
  rollback`, mail send test.
- **Phase 14R — 48-hour watch.** Railway's built-in metrics dashboard
  shows CPU/memory/request volume. Add an external probe via
  [Healthchecks.io](https://healthchecks.io) hitting
  `https://api.versatexanalytics.com/api/health/` every 5 min.

## Differences from the Hetzner deploy

| Concern | Hetzner | Railway |
|---|---|---|
| VPS management | You | Railway |
| Postgres backups | `backup-postgres.sh` cron to R2 | Railway auto (1 daily, 7-day retention free tier) |
| Redis persistence | `appendonly yes` in compose | Railway managed |
| Rollback | `APP_VERSION=<prev-sha> docker compose pull` | Railway deployments tab → "Rollback" button |
| Scaling | Bigger VPS / add 2nd box | Resource sliders per service |
| Uptime probes | Self-hosted Kuma | External Healthchecks.io + Railway metrics |
| Cost (v1) | ~$7.50/mo | ~$25–45/mo usage-based |

## Files in the repo that are Hetzner-specific and unused on Railway

These stay in the repo for future optionality; they're not read by
Railway's pipeline:

- `docker-compose.prod.yml`
- `docker-compose.tunnel.yml`
- `docker-compose.monitoring.yml`
- `scripts/predeploy-snapshot.sh`
- `scripts/check-backup-freshness.sh`
- `scripts/capacity-check.sh`
- `scripts/backup-postgres.sh`
- `scripts/backup-media.sh`
- `docs/FIRST-DEPLOY-WALKTHROUGH.md`
- `docs/deployment/CLOUDFLARE-TUNNEL.md`

## Common Railway-specific pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `psql: FATAL: database "railway" does not exist` when connecting | Using `DATABASE_URL` vs `DATABASE_PUBLIC_URL` confusion | Always use `${{postgres.DATABASE_URL}}` (internal — fastest, free bandwidth); `DATABASE_PUBLIC_URL` is for external clients |
| `/api/health/` returns `"redis":"error"` | `CELERY_BROKER_URL` points at Railway's Redis on a different database number than the cache | Set all three Redis-consuming vars (`REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`) to the same `${{redis.REDIS_URL}}` |
| Static files 404 on admin | `collectstatic` didn't run | Ensure start command begins with `python manage.py collectstatic --noinput &&` |
| Deploy fails with "migrations pending" | Start command runs gunicorn before migrations | Chain migrate + collectstatic + gunicorn with `&&` in start command (as shown in 11R.2) |
| Frontend loads but API calls CORS-blocked | `CORS_ALLOWED_ORIGINS` doesn't match current frontend URL | Add frontend's full origin (with scheme + no trailing slash) to the env var; redeploy backend |
| pgvector extension disappears after DB restart | Was never properly installed | Re-run `CREATE EXTENSION IF NOT EXISTS vector;` via Data tab; extensions persist across restarts once installed |
| Custom domain stuck "Pending certificate" | DNS not resolving yet | Wait 5 more minutes. `dig api.versatexanalytics.com CNAME` to confirm DNS points at Railway |
| `railway run` fails with "Project not linked" | Haven't linked the local dir to the Railway project | `cd` to any dir and run `railway link`, select the project |
