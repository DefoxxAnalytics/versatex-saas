# First Deploy Walkthrough (Round C)

Step-by-step walkthrough for the first production bring-up on
Cloudflare Tunnel + Hetzner CX32. Picks up after `deploy/prep` has
merged to `main` and GHCR images are published.

Every step is checkpointed — you can pause between any two steps
without losing state. Natural pause points marked 🛑.

**Assumed before starting:**
- `deploy/prep` PR merged; GHCR images exist at
  `ghcr.io/defoxxanalytics/versatex-saas-{backend,frontend}:<sha>`
- GitHub repo variable `VITE_API_URL=/api` is set
- Phase 8 apex inventory is saved (baseline headers + DNS)
- `APP_VERSION` identified (use `git rev-parse --short HEAD` on `main`
  — GitHub produces 7-char short SHAs for image tags)

## Prerequisites checklist

Check all of these before dive-in.

- [ ] **Hetzner Cloud** account (payment method on file)
- [ ] **SSH public key** on your laptop. If not: `ssh-keygen -t ed25519 -C "your-email"` in Git Bash / WSL, accept defaults. Key lands at `~/.ssh/id_ed25519.pub`.
- [ ] **Cloudflare account** managing `versatexanalytics.com` (already exists)
- [ ] **GitHub account** with ability to create Personal Access Tokens
- [ ] **Password manager** (1Password or equivalent) open. You'll save ~10 credentials.
- [ ] **Phone with ntfy app** installed (free; iOS/Android)

**Time estimate:** ~3 hours end-to-end active work. Can span multiple
sessions if broken at checkpoints.

---

# PHASE 10 — VPS provision + Docker + GHCR (~45 min)

## 10.1 — Create the Hetzner VPS

1. Go to the Hetzner Cloud Console at `https://console.hetzner.cloud/`.
2. Create a project (first-time): name it `versatex-prod`.
3. Inside the project → **Add Server**:
   - **Location:** pick closest to your primary users. Ashburn (USA),
     Falkenstein (Germany), or Helsinki (Finland) are typical. Cannot
     be changed after creation.
   - **Image:** Ubuntu → **Ubuntu 24.04**
   - **Type:** Shared vCPU → **CX32** (4 vCPU, 8 GB RAM, 80 GB disk,
     ~€6.80/mo). CX22 is too tight — plan's capacity appendix shows
     peak usage exceeds 4 GB during nightly batch + backup overlap.
   - **Networking:** IPv4 enabled (adds ~€0.50/mo; needed for Phase 13
     curl tests from your laptop).
   - **SSH key:** Click **Add SSH Key** → paste contents of
     `~/.ssh/id_ed25519.pub`. Name: `versatex-deploy-key`.
   - Skip volumes, firewalls, backups (Hetzner's native backups —
     we roll our own to R2), placement groups, cloud-config.
   - **Name:** `versatex-prod`
4. **Create & Buy Now.** Wait ~30 s for "Running" state.
5. **Copy the IPv4 address** from the server detail page. Save in
   1Password as "Versatex VPS IPv4".

🛑 **Checkpoint 10.1:** VPS running, IPv4 recorded.

## 10.2 — First SSH + harden

Open Git Bash or WSL. Replace `<vps-ip>` everywhere with your IPv4.

```bash
# First login as root (only works from the SSH key you uploaded)
ssh root@<vps-ip>
```

Create the non-root deploy user and lock down SSH:

```bash
# Create deploy user with sudo
adduser deploy
# Strong password when prompted → save in 1Password as "Versatex VPS deploy sudo pw"
# Accept defaults for name/phone/etc (leave blank — press Enter)
usermod -aG sudo deploy

# Copy SSH key to the deploy user so it can log in with the same key
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy

# Disable root SSH + password auth
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

# Firewall: only port 22 open. Cloudflare Tunnel dials outbound,
# no inbound 80/443 needed.
ufw allow 22/tcp
ufw --force enable
ufw status
```

Expected `ufw status`:

```
Status: active
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
22/tcp (v6)                ALLOW       Anywhere (v6)
```

**Don't log out of the root session yet.** Test deploy-user login in a
**new terminal window**:

```bash
# NEW terminal — DON'T close the root session
ssh deploy@<vps-ip>
```

You should land in `/home/deploy`. If this succeeds:

```bash
# In the ROOT session, log out
exit
```

If the deploy login fails, fix `/etc/ssh/sshd_config` from the still-
open root session before logging out.

🛑 **Checkpoint 10.2:** Logged in as `deploy`. Root SSH disabled.
UFW allows only port 22.

## 10.3 — Install Docker

In the deploy-user SSH session:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker     # apply group membership without logout
docker --version
docker compose version
```

Expected: Docker 2X.X.X, Docker Compose v2.X.X.

🛑 **Checkpoint 10.3:** Docker runs without `sudo`.

## 10.4 — Generate GHCR Personal Access Token

On your laptop browser:

1. GitHub → top-right avatar → **Settings**
2. Left sidebar → scroll down → **Developer settings**
3. **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
4. Settings:
   - Token name: `versatex-vps-ghcr-read`
   - Expiration: `90 days`
   - Resource owner: `DefoxxAnalytics`
   - Repository access: Only select repositories → `versatex-saas`
   - **Permissions → Repository permissions:**
     - Contents: No access
     - Metadata: Read-only (auto-required)
     - **Packages: Read-only** ← critical
     - Leave all other permissions as "No access"
5. **Generate token** → **copy immediately**. Save in 1Password as
   "Versatex GHCR read-only PAT".

⚠️ Token is shown once. If you navigate away without copying,
regenerate.

🛑 **Checkpoint 10.4:** PAT saved.

## 10.5 — Clone repo + GHCR login

Back in the VPS SSH session:

```bash
cd ~
git clone https://github.com/DefoxxAnalytics/versatex-saas.git
cd versatex-saas
git log --oneline -3
# Expected: the merge commit at the top
```

GHCR login — replace `<PAT>` with the token from 10.4:

```bash
echo "<PAT>" | docker login ghcr.io -u DefoxxAnalytics --password-stdin
```

Expected: `Login Succeeded`.

Verify the image pull works. Replace `<sha>` with your target
`APP_VERSION` (7-char short SHA on main):

```bash
docker pull ghcr.io/defoxxanalytics/versatex-saas-backend:<sha>
docker pull ghcr.io/defoxxanalytics/versatex-saas-frontend:<sha>
# Expected: "Status: Downloaded newer image..." for each
```

Failure here usually means:
- PAT scope wrong → regenerate with Packages: Read-only
- Image tag doesn't exist → verify at `https://github.com/orgs/DefoxxAnalytics/packages`

🛑 **Checkpoint 10.5:** Both images pulled. **Phase 10 complete.**

Good natural break point. Return when ready for Phase 11.

---

# PHASE 11 — First prod bring-up (~90 min)

Nine sub-steps. Each ends at a checkpoint.

## 11.1 — Cloudflare Tunnel creation

Cloudflare dashboard:

1. Top-left account dropdown → select your account (not the zone).
2. Left sidebar → **Zero Trust** (opens a separate dashboard). First
   visit prompts for a team name → use `versatex` or similar.
3. Zero Trust → **Networks** → **Tunnels** → **Create a tunnel**
4. Connector type: **Cloudflared** → **Next**
5. Tunnel name: `versatex-prod` → **Save tunnel**
6. **Copy the tunnel token** (long base64 string, `eyJhIjoi...`).
   Save in 1Password as "Versatex CF Tunnel token".

⚠️ Token is shown once. If missed, delete the tunnel and recreate.

7. On the "Choose your environment" screen, click **Next** (we don't
   install cloudflared manually — it runs in Docker).
8. **Route tunnel → Public Hostnames:**
   - **Add a public hostname:**
     - Subdomain: `app`
     - Domain: `versatexanalytics.com`
     - Path: empty
     - Service type: `HTTP`
     - URL: `frontend:80`
     - **Save hostname**
   - **Add a public hostname** again:
     - Subdomain: `monitor`
     - Domain: `versatexanalytics.com`
     - Path: empty
     - Service type: `HTTP`
     - URL: `uptime-kuma:3001`
     - **Save hostname**
9. Don't click "Complete installation" at the bottom — done with this
   page.

🛑 **Checkpoint 11.1:** Tunnel `versatex-prod` exists with 2 public
hostnames mapped. Token saved.

## 11.2 — Cloudflare Access applications

Still in Zero Trust dashboard:

1. Left sidebar → **Access** → **Applications** → **Add an application**
   → **Self-hosted**

2. **Application 1 — Versatex Admin**
   - Application name: `Versatex Admin`
   - Session duration: `24 hours`
   - Application domain: `app.versatexanalytics.com`
   - Path: `manage-` (placeholder — we fix this in 11.6 once
     ADMIN_URL is generated)
   - Identity providers: enable **One-time PIN** (default)
   - **Next**
   - Policy name: `Admins`
   - Action: `Allow`
   - Include → **Emails** → add your email + one backup
   - **Next → Add application**

3. **Application 2 — Versatex Monitor**
   - Application name: `Versatex Monitor`
   - Session duration: `24 hours`
   - Application domain: `monitor.versatexanalytics.com`
   - Path: empty (entire monitor subdomain is gated)
   - Identity providers: One-time PIN
   - Policy: same email list
   - **Add application**

🛑 **Checkpoint 11.2:** Two Access applications exist. (Path for the
Admin app is a placeholder — we fix it in 11.6.)

## 11.3 — R2 buckets + API token

Cloudflare dashboard → back to main dashboard (not Zero Trust):

1. Left sidebar → **R2 Object Storage**. First visit: accept terms +
   add a payment method. Free tier covers 10 GB — won't charge in v1.
2. **Create bucket** × 2:
   - Name: `versatex-backups` | Location: Automatic | Standard class
     → **Create bucket**
   - Name: `versatex-media` | Location: Automatic | Standard class
     → **Create bucket**
3. **Manage R2 API Tokens** (button at top-right of R2 overview):
   - **Create API token**
   - Token name: `versatex-vps-r2`
   - Permissions: **Object Read & Write**
   - Specify bucket: **Apply to specific buckets only** → select both
     `versatex-backups` AND `versatex-media`
   - TTL: Forever (or 1 year)
   - **Create API Token**
4. Copy THREE values → save in 1Password:
   - **Access Key ID**
   - **Secret Access Key**
   - **S3 API endpoint URL** — `https://<account-id>.r2.cloudflarestorage.com`
     (visible at the top of the R2 overview page under "S3 API")

🛑 **Checkpoint 11.3:** Two R2 buckets exist. Token (3 values) saved.

## 11.4 — Resend account + domain verification

Resend free tier: 3k emails/month.

1. `https://resend.com/` → **Get Started** → sign up with GitHub or email.
2. **Domains** → **Add Domain** → `versatexanalytics.com` → **Add**.
3. Resend shows three DNS records (SPF, DKIM, DMARC). Copy them.
4. **Another tab** — Cloudflare dashboard → `versatexanalytics.com`
   → **DNS → Records** → **Add record** × 3:
   - Each record's Type / Name / Content / TTL are given by Resend.
     Copy verbatim.
   - **Proxy status: DNS only (grey cloud)** for all three — SPF/DKIM/
     DMARC must not be proxied.
5. Back in Resend → **Verify DNS Records**. Usually propagates within
   60 s. Retry if needed.
6. **API Keys** → **Create API key**:
   - Name: `versatex-smtp`
   - Permission: Sending access
   - Domain: `versatexanalytics.com`
   - **Create**
7. Copy the API key (starts with `re_`) → save in 1Password as
   "Versatex Resend API key".

Resend SMTP config:
- Host: `smtp.resend.com`
- Port: `587`
- Username: `resend` (literal string)
- Password: the `re_...` API key

🛑 **Checkpoint 11.4:** Domain verified. API key saved.

## 11.5 — Generate secrets

Back on the VPS. Run each, save each output in 1Password before moving
on.

```bash
# SECRET_KEY (Django)
docker run --rm python:3.12-slim python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Save → "Versatex SECRET_KEY"

# DB_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Save → "Versatex DB_PASSWORD"

# REDIS_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Save → "Versatex REDIS_PASSWORD"

# FLOWER_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Save → "Versatex FLOWER_PASSWORD"

# FIELD_ENCRYPTION_KEY (Fernet-compatible)
docker run --rm python:3.12-slim sh -c "pip install -q cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
# Save → "Versatex FIELD_ENCRYPTION_KEY"

# ADMIN_URL — obscured admin path
python3 -c "import secrets; print(f'manage-{secrets.token_hex(8)}/')"
# Save → "Versatex ADMIN_URL" (e.g. manage-3f2b1a7c9d4e6f80/)
```

**Now update the Cloudflare Access Admin app's Path** (deferred from
11.2):

- Cloudflare Zero Trust → Access → Applications → edit
  `Versatex Admin` → Path field → paste `<your-ADMIN_URL>*` (note the
  `*` suffix for wildcard match; example:
  `manage-3f2b1a7c9d4e6f80/*`) → Save.

🛑 **Checkpoint 11.5:** 6 generated secrets saved. Access Admin path
updated.

## 11.6 — Assemble `.env`

On VPS:

```bash
cd ~/versatex-saas
cp .env.example .env
chmod 600 .env
nano .env      # or vim
```

Fill in placeholders from 1Password. Complete template:

```env
# Django
SECRET_KEY=<SECRET_KEY from 11.5>
DEBUG=False
ALLOWED_HOSTS=app.versatexanalytics.com
ADMIN_URL=<ADMIN_URL from 11.5>
FRONTEND_URL=https://app.versatexanalytics.com

# Database
DB_NAME=analytics_db
DB_USER=analytics_user
DB_PASSWORD=<DB_PASSWORD from 11.5>
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_PASSWORD=<REDIS_PASSWORD from 11.5>
CELERY_BROKER_URL=redis://:<REDIS_PASSWORD literal>@redis:6379/0
CELERY_RESULT_BACKEND=redis://:<REDIS_PASSWORD literal>@redis:6379/0

# CORS / CSRF
CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com
CSRF_TRUSTED_ORIGINS=https://app.versatexanalytics.com

# HSTS — start both False; flip to True after 1 week post-Phase 14
HSTS_INCLUDE_SUBDOMAINS=False
HSTS_PRELOAD=False

# Field encryption
FIELD_ENCRYPTION_KEY=<FIELD_ENCRYPTION_KEY from 11.5>

# Flower (celery monitoring)
FLOWER_USER=admin
FLOWER_PASSWORD=<FLOWER_PASSWORD from 11.5>

# Cloudflare Tunnel
CLOUDFLARED_TOKEN=<tunnel token from 11.1>

# Docker image version
APP_VERSION=<sha>

# Email (Resend)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<Resend API key from 11.4>
DEFAULT_FROM_EMAIL=Versatex Analytics <noreply@versatexanalytics.com>
SERVER_EMAIL=alerts@versatexanalytics.com

# R2 media storage
USE_R2_MEDIA=True
R2_MEDIA_BUCKET=versatex-media
R2_ENDPOINT=<R2 endpoint URL from 11.3>
R2_ACCESS_KEY_ID=<R2 Access Key ID from 11.3>
R2_SECRET_ACCESS_KEY=<R2 Secret Access Key from 11.3>

# LLM keys (optional — leave blank if you haven't signed up for providers)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# LLM cost digest webhook (set after ntfy setup below)
COST_ALERT_WEBHOOK_URL=
```

Save, then verify file permissions:

```bash
ls -la .env
# Expected: -rw------- 1 deploy deploy ...
```

**Optional — ntfy topic for alerts** (30 s):

1. Phone: open ntfy app → Subscribe → enter a random topic name like
   `versatex-alerts-4f8a2b1c`. Treat as shared secret — anyone with
   the topic can read messages.
2. Add to `.env`:

   ```
   COST_ALERT_WEBHOOK_URL=https://ntfy.sh/versatex-alerts-4f8a2b1c
   ```

3. Test from laptop:

   ```bash
   curl -d "setup test" https://ntfy.sh/versatex-alerts-4f8a2b1c
   ```

   Phone receives push within 5 s.

🛑 **Checkpoint 11.6:** `.env` fully populated, mode 600.

## 11.7 — Start the stack

On VPS:

```bash
cd ~/versatex-saas

# Load .env into current shell so APP_VERSION is visible to compose
set -a; source .env; set +a

# Pull all images first — catches auth issues before service startup
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  -f docker-compose.monitoring.yml \
  pull

# Bring it up
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  -f docker-compose.monitoring.yml \
  up -d db redis backend celery flower frontend cloudflared uptime-kuma

# Watch status for ~90s; all 8 services should become (healthy)
watch -n 5 docker compose ps
# Ctrl+C when all healthy
```

**If backend stays `(starting)` beyond 2 minutes:**

```bash
docker compose logs backend --tail 50
```

Look for `ImproperlyConfigured` errors — almost always a `.env` issue
(missing value, wrong format). Fix `.env`, then:

```bash
docker compose up -d backend
```

🛑 **Checkpoint 11.7:** All 8 services healthy.

## 11.8 — Migrate + superuser

```bash
# Apply migrations
docker compose exec backend python manage.py migrate

# (collectstatic is automatic since v3.1: backend/entrypoint.sh runs it
#  on every container start. Manual run only useful if you've changed
#  files under backend/static/ since the last container restart.)

# Create superuser
docker compose exec backend python manage.py createsuperuser
# Prompts for username, email, password. Save in 1Password.

# Link UserProfile (the app requires this)
docker compose exec backend python manage.py shell <<'PY'
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

Expected final line: `Linked <username> to Default Organization (role=admin)`.

🛑 **Checkpoint 11.8:** Migrations applied, superuser created,
profile linked.

## 11.9 — Smoke test

From your laptop:

```bash
# Transport — expect HTTP/2 200 (possibly after 301→200)
curl -IL https://app.versatexanalytics.com/

# Health
curl -s https://app.versatexanalytics.com/api/health/
# Expected: {"db": "ok", "redis": "ok"}

# Admin gate — replace <ADMIN_URL>
curl -IL https://app.versatexanalytics.com/<ADMIN_URL>login/
# Expected: 302 to a cloudflareaccess.com URL (OTP challenge)
```

Browser:

1. Incognito → `https://app.versatexanalytics.com/` → login page renders
2. Log in with superuser creds → dashboard (empty is fine — no data yet)
3. `https://app.versatexanalytics.com/<ADMIN_URL>login/` → redirects to
   Cloudflare Access → email OTP → admin login page → login
4. `https://monitor.versatexanalytics.com/` → Access OTP first, then
   Uptime Kuma setup wizard (see [MONITORING.md](deployment/MONITORING.md) for
   probe setup).

🛑 **Checkpoint 11.9:** All smoke tests pass. **Phase 11 complete.**
**App reachable at `https://app.versatexanalytics.com/`.**

---

# PHASE 12 — Cloudflare edge rules (~45 min)

Full detail in [CLOUDFLARE-EDGE.md](deployment/CLOUDFLARE-EDGE.md). Quick
walkthrough:

## 12.1 — SSL/TLS Full (strict)

Before flipping: verify marketing origin cert is valid.

```bash
curl -Iv https://versatexanalytics.com/ 2>&1 | grep -E "subject|issuer" | head -4
```

Expected: a valid issuer name (Let's Encrypt / Google Trust / Cloudflare
/ similar), NOT "self signed".

Switch: Cloudflare dashboard → `versatexanalytics.com` zone → **SSL/TLS
→ Overview** → **Full (strict)**.

Wait 60 s, reload marketing homepage. Verify nothing regresses.

## 12.2 — Cache Rules

Dashboard → **Rules → Cache Rules → Create rule**.

**Rule 1 — Cache static assets**

- Rule name: `versatex-app — cache static assets`
- If incoming requests match:
  - Hostname equals `app.versatexanalytics.com`
  - AND URI Path starts with `/assets/`
- Then: **Eligible for cache**
- Edge TTL: Override origin → 1 year
- Browser TTL: 1 year
- **Deploy**

**Rule 2 — Bypass cache on dynamic**

- Rule name: `versatex-app — bypass cache on dynamic`
- Use the Expression Editor (not the builder) — paste:

  ```
  (http.host eq "app.versatexanalytics.com" and (http.request.uri.path in {"/" "/index.html"} or starts_with(http.request.uri.path, "/api/") or starts_with(http.request.uri.path, "/admin/") or starts_with(http.request.uri.path, "/media/")))
  ```

- Then: **Bypass cache**
- **Deploy**

## 12.3 — Bot Fight Mode

Dashboard → **Security → Bots → Bot Fight Mode** → **On**.

(Managed Ruleset already on from Phase 8 inventory — leave it.)

## 12.4 — Rate Limiting

Dashboard → **Security → WAF → Rate limiting rules → Create rule**.

- Rule name: `versatex-app — login throttle`
- Expression (replace `<ADMIN_URL>` with your literal path from
  `.env`, e.g. `manage-3f2b1a7c9d4e6f80/`):

  ```
  (http.host eq "app.versatexanalytics.com" and (starts_with(http.request.uri.path, "/api/v1/auth/login/") or starts_with(http.request.uri.path, "/<ADMIN_URL>login")))
  ```

- Rate: `10` requests per `10 minutes` per IP
- Action: **Block**
- Duration: `10 minutes`
- **Deploy**

## 12.5 — Verify

```bash
# Cache working — first request cold, second within 60s should HIT
curl -sI https://app.versatexanalytics.com/assets/index-<hash>.js \
  | grep -i cf-cache-status
# First: MISS; Second: HIT

# API bypass
curl -sI https://app.versatexanalytics.com/api/health/ \
  | grep -i cf-cache-status
# Expected: BYPASS

# Rate limit (WARNING: locks your IP for 10 min after triggering)
for i in $(seq 1 11); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    https://app.versatexanalytics.com/api/v1/auth/login/ \
    -d '{"username":"x","password":"x"}' -H 'Content-Type: application/json')
  echo "Attempt $i: $code"
done
# Expected: first 10 → 400/401, 11th → 429
# Wait 10 min before real testing
```

🛑 **Checkpoint 12:** Edge rules applied and verified.
**Phase 12 complete.**

---

## What's next

Round C complete. The app is live, gated, cached, and rate-limited.
Round D (Phase 13 verification + Phase 14 48h watch) follows.

- **[DEPLOY-PLAYBOOK.md](deployment/DEPLOY-PLAYBOOK.md)** — routine deploys,
  rollbacks, migration safety, secret rotation, failure diagnoses.
- **[MONITORING.md](deployment/MONITORING.md)** — probe setup inside Uptime Kuma,
  external probe, weekly metrics review.
- **[CLOUDFLARE-EDGE.md](deployment/CLOUDFLARE-EDGE.md)** — full reference for the
  rules applied above, plus verification and rollback per change.
- **[BACKUPS-AND-MEDIA.md](deployment/BACKUPS-AND-MEDIA.md)** — install the
  nightly postgres + media backup cron jobs.

## Common first-deploy problems

| Symptom | Likely cause | Fix |
|---|---|---|
| `docker pull` returns `denied` | GHCR PAT lacks `packages:read` | Regenerate PAT (10.4) with correct scope |
| `curl https://app.*/api/health/` returns 521 (web server is down) | Tunnel not connected | Zero Trust → Networks → Tunnels → check status is HEALTHY; verify `CLOUDFLARED_TOKEN` in `.env` matches |
| Infinite redirect on login | `X-Forwarded-Proto` not propagating | Confirm `frontend/nginx/nginx.conf` has the map block (Phase 3 added); check container image tag matches commit |
| `/api/health/` returns 503 with `"redis":"error"` | Redis password mismatch between `.env` and `CELERY_BROKER_URL` | `.env` must duplicate the password literal in `CELERY_BROKER_URL` — Docker Compose doesn't interpolate from the same file |
| Admin page 404s | `ADMIN_URL` mismatch between `.env` and the URL you're hitting | Use the exact value from `.env`: `/<ADMIN_URL>login/` |
| Email `send_mail` raises SMTPAuthenticationError | Resend SMTP format changed | `EMAIL_HOST_USER=resend` (literal), `EMAIL_HOST_PASSWORD=re_...` (the API key). Verify Resend's current SMTP docs |
| Migrations crash on `IvfflatIndex` | SQLite detected | Should not happen in prod; confirm `DB_ENGINE` resolved to `postgresql` (check `settings.py`) |
