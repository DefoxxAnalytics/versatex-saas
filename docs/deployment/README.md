# Deployment

Guides for deploying Versatex Analytics to production.

## Options at a glance

| Option | Best for | Monthly cost | Setup time | Guide |
|--------|----------|--------------|------------|-------|
| **Railway** | Managed PaaS, no sysadmin work | $30-65 | ~1 hour | [RAILWAY.md](RAILWAY.md) |
| **Cloudflare + Hetzner** | Cheapest; reuse an existing Cloudflare-managed domain | ~$5 | 2-3 hours | [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md) |

Both setups end up with the same Django + Celery + Postgres + Redis stack running behind HTTPS on a domain you control.

## Which should I pick?

**Railway** if:

- You don't have an ops engineer.
- You want managed Postgres + Redis + automated backups out of the box.
- $30-65/mo is within budget.

**Cloudflare + Hetzner** if:

- You already host something on Cloudflare (e.g. a marketing page on `versatexanalytics.com`) and want the app on a subdomain.
- You're comfortable running `docker-compose` on Linux.
- You want to stay under $10/mo.

## Cloudflare + Hetzner documents

Read these in order:

1. [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md) — End-to-end walkthrough. Start here.
2. [CLOUDFLARE-DNS.md](CLOUDFLARE-DNS.md) — Adding `app.*` and `api.*` subdomains alongside an existing site on the apex.
3. [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md) — Zero-trust tunnel reference (no open ports on the VPS).
4. [CLOUDFLARE-PAGES.md](CLOUDFLARE-PAGES.md) — Deploying the React frontend on Pages (free tier).
5. [BACKUPS-AND-MEDIA.md](BACKUPS-AND-MEDIA.md) — Postgres backups to R2, media file persistence.

## Railway documents

- [RAILWAY.md](RAILWAY.md) — Reference guide.
- [RAILWAY-STEP-BY-STEP.md](RAILWAY-STEP-BY-STEP.md) — First-time walkthrough.
