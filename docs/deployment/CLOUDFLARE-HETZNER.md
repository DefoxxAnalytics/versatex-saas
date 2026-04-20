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
git clone https://github.com/<your-org>/Versatex-Analytics.git
cd Versatex-Analytics
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
```

Edit `.env` on the VPS with the generated values:

```env
SECRET_KEY=<generated>
DEBUG=False
ALLOWED_HOSTS=api.versatexanalytics.com

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
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  up -d --build

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
admin = User.objects.get(username="admin")
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
- [ ] Django admin reachable at `https://api.versatexanalytics.com/admin/`.
- [ ] Celery Beat + worker logs show scheduled tasks firing (v2.9 batch jobs run 2-4 AM).

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
