# Cloudflare + Hetzner Deployment

End-to-end recipe for hosting Versatex Analytics on a single Hetzner VPS, fronted by Cloudflare. Designed to run alongside an existing marketing site on the same Cloudflare-managed apex domain.

## Why this setup

- **Cheap.** ~$5/mo total. The VPS is the only recurring cost; Cloudflare DNS, Pages, Tunnel, and R2 are free at this scale.
- **Zero refactor.** The repo already ships `docker-compose.yml` and `docker-compose.prod.yml`. We reuse them as-is.
- **No open ports.** Cloudflare Tunnel dials outbound from the VPS, so the firewall stays closed to the public internet (except SSH, optional).
- **Subdomain isolation.** The marketing site on `versatexanalytics.com` is untouched. The app lives on `app.versatexanalytics.com` and `api.versatexanalytics.com`.

## Architecture

```
Browser
   │
   ▼
Cloudflare edge (DNS + proxy + TLS)
   │
   ├── versatexanalytics.com          → existing marketing site (unchanged)
   ├── app.versatexanalytics.com      → Cloudflare Pages (React build)
   └── api.versatexanalytics.com      → Cloudflare Tunnel
                                            │
                                            ▼
                                     Hetzner VPS (docker-compose)
                                            │
                                  ┌─────────┼─────────┐
                                  ▼         ▼         ▼
                               backend    celery   flower
                                  │         │
                                  └────┬────┘
                                       ▼
                                   postgres
                                       │
                                     redis
```

## Cost

| Item | Provider | Monthly |
|------|----------|---------|
| VPS (CX22: 2 vCPU, 4 GB RAM, 40 GB disk) | Hetzner | ~$5 (€4.51) |
| DNS, proxy, TLS, WAF | Cloudflare | $0 |
| Tunnel (unlimited hostnames) | Cloudflare | $0 |
| Pages (unlimited bandwidth, 500 builds/mo) | Cloudflare | $0 |
| R2 storage (10 GB free tier) | Cloudflare | $0 |
| **Total** | | **~$5** |

Upgrade to CX32 (8 GB RAM, ~$8) if Celery + Postgres + Redis contend for memory under real load.

## Prerequisites

- Cloudflare account with `versatexanalytics.com` (or equivalent) already managed by it.
- Hetzner Cloud account with an SSH key uploaded.
- GitHub repo (for Cloudflare Pages auto-deploy).
- Local machine with `ssh`, `git`, and a text editor.

## Walkthrough

### 1. Provision the VPS

1. Hetzner Cloud Console → **Create server**.
2. Location: nearest your users (Ashburn, Falkenstein, Helsinki).
3. Image: **Ubuntu 24.04**.
4. Type: **CX22** to start, **CX32** if you need headroom.
5. SSH key: select the one you uploaded.
6. Name: `versatex-prod`.
7. Create. Note the IPv4 address.

### 2. Harden the VPS

SSH in as root:

```bash
ssh root@<hetzner-ipv4>
```

Create a non-root user and lock down SSH:

```bash
adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy

sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

# Firewall: only SSH is needed. Cloudflare Tunnel dials outbound.
ufw allow 22/tcp
ufw --force enable
```

Log out and back in as `deploy`:

```bash
ssh deploy@<hetzner-ipv4>
```

### 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

### 4. Clone the repo

```bash
cd ~
git clone https://github.com/DefoxxAnalytics/versatex-analytics.git
cd versatex-analytics
cp .env.example .env
```

### 5. Generate production secrets

The easiest way is to run one-off commands inside a throwaway Python container:

```bash
# SECRET_KEY (Django)
docker run --rm python:3.12-slim python -c "from secrets import choice; import string; print(''.join(choice(string.ascii_letters + string.digits + '@#%^*(-_=+)') for _ in range(50)))"

# DB_PASSWORD and REDIS_PASSWORD
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(32))"

# FIELD_ENCRYPTION_KEY
docker run --rm python:3.12-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
  || docker run --rm python:3.12-slim sh -c "pip install -q cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"

# ADMIN_URL (stable obscured admin path — see the Admin panel section below; leaving this blank rotates the URL on every restart)
docker run --rm python:3.12-slim python -c "import secrets; print(f'manage-{secrets.token_hex(8)}/')"
```

Edit `.env` on the VPS with the generated values:

```env
SECRET_KEY=<generated>
DEBUG=False
ALLOWED_HOSTS=api.versatexanalytics.com
ADMIN_URL=<generated>

DB_NAME=analytics_db
DB_USER=analytics_user
DB_PASSWORD=<generated>
DB_HOST=db
DB_PORT=5432

REDIS_PASSWORD=<generated>
CELERY_BROKER_URL=redis://:<redis-password>@redis:6379/0
CELERY_RESULT_BACKEND=redis://:<redis-password>@redis:6379/0

CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com
CSRF_TRUSTED_ORIGINS=https://app.versatexanalytics.com
FRONTEND_URL=https://app.versatexanalytics.com

FIELD_ENCRYPTION_KEY=<generated>

FLOWER_USER=admin
FLOWER_PASSWORD=<generated>
```

Permissions:

```bash
chmod 600 .env
```

### 6. Set up Cloudflare Tunnel

Full walkthrough in [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md). Short version:

1. Zero Trust dashboard → **Networks** → **Tunnels** → **Create a tunnel** (type: cloudflared, name: `versatex-prod`).
2. Copy the tunnel token.
3. Add `CLOUDFLARED_TOKEN=<token>` to `.env`.
4. Add a `cloudflared` sidecar via `docker-compose.tunnel.yml` (snippet in [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md)).
5. In the tunnel's **Public Hostnames** tab, map:
   - `api.versatexanalytics.com` → `http://backend:8000`

### 7. Start the stack

```bash
# Start only the backend stack — the React frontend lives on Cloudflare Pages,
# so skip the frontend container and the optional nginx (profile: production).
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  up -d --build db redis backend celery flower cloudflared

docker compose ps
docker compose logs -f backend
```

Wait for services to report healthy. Run migrations and create a superuser:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic --noinput
docker compose exec backend python manage.py createsuperuser
```

Link the superuser to an initial organization:

```bash
docker compose exec backend python manage.py shell <<'PY'
from apps.authentication.models import Organization, UserProfile
from django.contrib.auth import get_user_model
User = get_user_model()
org, _ = Organization.objects.get_or_create(slug="default", defaults={"name": "Default Organization"})
admin = User.objects.filter(is_superuser=True).order_by("id").first()
if admin is None:
    raise SystemExit("No superuser found; run createsuperuser first.")
UserProfile.objects.get_or_create(
    user=admin,
    defaults={"organization": org, "role": "admin", "is_active": True},
)
PY
```

### 8. Add DNS records

See [CLOUDFLARE-DNS.md](CLOUDFLARE-DNS.md). Two records under `versatexanalytics.com`:

| Type  | Name  | Content                          | Proxy |
|-------|-------|----------------------------------|-------|
| CNAME | `app` | `<project>.pages.dev`            | on    |
| CNAME | `api` | `<tunnel-id>.cfargotunnel.com`   | on    |

Both are created automatically — `app` when you attach the custom domain in Pages, `api` when you map the public hostname in Tunnel. You do not need to create them by hand.

### 9. Deploy the frontend

Full walkthrough in [CLOUDFLARE-PAGES.md](CLOUDFLARE-PAGES.md). Short version:

- Pages → **Create application** → **Connect to Git** → select the repo.
- Build command: `cd frontend && corepack enable && pnpm install --frozen-lockfile && pnpm build`
- Build output directory: `frontend/dist`
- Environment variables:
  - `VITE_API_URL=https://api.versatexanalytics.com/api`
  - `VITE_APP_TITLE=Versatex Analytics`
  - `VITE_APP_LOGO=/vtx_logo2.png`
  - `NODE_VERSION=20`
- Custom domain: `app.versatexanalytics.com`.

### 10. Verify

```bash
curl -I https://app.versatexanalytics.com
curl -I https://api.versatexanalytics.com/admin/login/

dig +short app.versatexanalytics.com   # Cloudflare IPs
dig +short api.versatexanalytics.com   # Cloudflare IPs
```

Open `https://app.versatexanalytics.com` and log in as the superuser.

### 11. Set up backups

See [BACKUPS-AND-MEDIA.md](BACKUPS-AND-MEDIA.md). Nightly `pg_dump` to Cloudflare R2 via `rclone`, plus a strategy for the media volume.

## Production checklist

Before sharing the URL with real users:

- [ ] `DEBUG=False` in `.env`.
- [ ] `SECRET_KEY`, `DB_PASSWORD`, `REDIS_PASSWORD`, `FIELD_ENCRYPTION_KEY` are freshly generated (no `.env.example` defaults).
- [ ] `ALLOWED_HOSTS` set to the API subdomain only.
- [ ] `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` use `https://` and match the app subdomain exactly.
- [ ] `docker-compose.prod.yml` used (removes public Postgres/Redis ports, adds resource limits, enforces read-only frontend filesystem).
- [ ] UFW enabled on the VPS, only port 22 open.
- [ ] Cloudflare Tunnel shows **HEALTHY** in the Zero Trust dashboard.
- [ ] Nightly `pg_dump` cron scheduled and a restore drill completed (see [BACKUPS-AND-MEDIA.md](BACKUPS-AND-MEDIA.md)).
- [ ] Superuser created and linked to an `Organization` via `UserProfile`.
- [ ] Django admin reachable at `https://api.versatexanalytics.com/<ADMIN_URL>/` (gated by Cloudflare Access if configured).
- [ ] Celery worker running — but note the Celery Beat gap below; scheduled tasks need extra setup.
- [ ] `ADMIN_URL` set to a stable random path (see [Admin panel](#admin-panel)).
- [ ] Cloudflare Access policy covers `<ADMIN_URL>*` (recommended).

## Admin panel

Django admin is served by the backend at `https://api.versatexanalytics.com/<ADMIN_URL>/` through the same Cloudflare Tunnel as the API. `whitenoise` serves admin's static assets inside gunicorn — no separate static-file server needed.

### Stable admin URL

Set `ADMIN_URL` to a fixed random string in `.env`. If left empty, [`backend/config/settings.py`](../../backend/config/settings.py) generates a new `manage-<hex>/` path **on every container restart** and only logs it — impractical once the site is live and impossible to bookmark.

Generate a stable value once:

```bash
docker run --rm python:3.12-slim python -c "import secrets; print(f'manage-{secrets.token_hex(8)}/')"
```

Paste into `.env` as `ADMIN_URL=manage-<hex>/` (trailing slash required) and restart the backend.

### Gate with Cloudflare Access (recommended)

Admin is the primary data-ingestion surface — CSV uploads for transactions and P2P records flow through it. Put it behind Cloudflare Access for free email-OTP or SSO layered in front of Django's own login.

1. Zero Trust dashboard → **Access** → **Applications** → **Add an application** → **Self-hosted**.
2. Application settings:
   - Application name: `Versatex Admin`
   - Session duration: 24h
   - Application domain: `api.versatexanalytics.com`
   - Path: `<ADMIN_URL>*` (e.g. `manage-3f2b1a7c9d4e6f80/*`)
3. Identity providers: enable at least one — email one-time PIN is enough to start; layer in Google Workspace, GitHub, or Okta later.
4. Policies → **Add a policy**:
   - Name: `Admins`
   - Action: **Allow**
   - Rule: **Emails** in list — add each team member's email.
5. Save. Reaching admin now requires an OTP code sent to an allowed email **before** Cloudflare forwards the request to Django.

Free tier covers 50 seats, ample for a single-org deployment.

### CSV upload size limits

Admin's CSV import buttons go through the tunnel, which caps request bodies. Cloudflare's defaults:

| Plan | Max request body |
|------|------------------|
| Free / Pro / Business | 100 MB |
| Enterprise | 500 MB |

For files larger than 100 MB, bypass the tunnel and use the management command over SSH. Copy the CSV onto the VPS first:

```bash
scp big-transactions.csv deploy@<hetzner-ipv4>:/home/deploy/versatex-analytics/
```

Then import from inside the backend container:

```bash
ssh deploy@<hetzner-ipv4>
cd versatex-analytics
docker compose cp big-transactions.csv backend:/tmp/
docker compose exec backend python manage.py import_p2p_data \
  --org-slug <slug> --type <pr|po|gr|invoice> --file /tmp/big-transactions.csv
```

### Gunicorn timeout

Gunicorn runs with `--timeout 120` (two minutes). Synchronous admin actions that exceed this are killed by the worker. If you add slow bulk admin actions, defer them to Celery rather than blocking the request.

### Verify admin works end-to-end

```bash
# With Access: first request 302s to Cloudflare Access login, then 200 for Django
# Without Access: first request 200 straight to Django login
curl -IL https://api.versatexanalytics.com/<ADMIN_URL>/
```

In a browser: navigate to the URL, complete Cloudflare Access OTP (if configured), then sign in with the Django superuser from Step 7.

## Known gaps

### Celery Beat is not started

[`backend/config/celery.py`](../../backend/config/celery.py) defines a `beat_schedule` for the v2.9 AI-insight batch jobs (generation at 02:00, enhancement at 02:30, semantic-cache cleanup at 03:00, log cleanup at 03:30, RAG refresh Sundays at 04:00). But [`docker-compose.yml`](../../docker-compose.yml) only runs `celery -A config worker -l info` — no `-B` flag, no separate beat service. Scheduled tasks **do not run** out of the box.

Pick one fix:

1. **Embed beat in the worker** (simplest, fine for a single-VPS deployment). Override the `celery` service command in `docker-compose.prod.yml`:

   ```yaml
   celery:
     command: celery -A config worker -B -l info
   ```

   Trade-off: if the worker dies, beat dies with it. Celery docs recommend splitting them at scale — but for one-box deployments this is acceptable.

2. **Add a dedicated beat service** (recommended if you run multiple workers). Append to `docker-compose.prod.yml`:

   ```yaml
   celery-beat:
     build:
       context: ./backend
       dockerfile: Dockerfile
     container_name: analytics-celery-beat
     command: celery -A config beat -l info
     env_file:
       - .env
     environment:
       - DB_HOST=db
       - DB_PORT=5432
       - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-changeme}@redis:6379/0
       - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD:-changeme}@redis:6379/0
     depends_on:
       - db
       - redis
     networks:
       - internal
       - default
   ```

   Remember to include it in the `docker compose ... up -d` service list.

### Backend healthcheck ties to `ADMIN_URL`

[`docker-compose.prod.yml`](../../docker-compose.prod.yml) now overrides the backend healthcheck to hit `/${ADMIN_URL}login/` instead of `/admin/login/`, so it follows the obscured path. This means `ADMIN_URL` must be set in `.env` **before** `docker compose up -d`, or the healthcheck URL becomes `/login/` and returns 404.

## Troubleshooting

### 502 Bad Gateway from `api.versatexanalytics.com`

Tunnel is up but cannot reach the backend container.

```bash
docker compose ps
docker compose logs cloudflared --tail=50
docker compose logs backend --tail=50
```

The tunnel's public hostname service must be `http://backend:8000` (the Docker service name), **not** `localhost` or the VPS IP.

### 530 or 1033 from Cloudflare

The tunnel isn't connected. Check `cloudflared` logs for auth errors (bad `TUNNEL_TOKEN`) or network errors, and the tunnel health in the Zero Trust dashboard.

### CORS errors in the browser

The Pages domain and the `CORS_ALLOWED_ORIGINS` value must match exactly, including scheme. Don't mix `http://` and `https://`, and don't include a trailing slash.

### Celery tasks stuck in pending

Verify the worker is up and the broker URL uses the authenticated Redis URL (`redis://:<password>@redis:6379/0`). Flower (optional extra tunnel hostname) shows worker status live.

### Out of memory

`docker stats` to identify the offender. Usual suspects: Postgres under load or Celery with too many concurrent tasks. Either upgrade to CX32 or lower Celery `--concurrency`.

## Links

- Hetzner Cloud pricing — https://www.hetzner.com/cloud
- Cloudflare Tunnel — https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare Pages — https://developers.cloudflare.com/pages/
- Cloudflare R2 — https://developers.cloudflare.com/r2/
