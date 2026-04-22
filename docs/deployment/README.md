# Deployment

Guides for deploying Versatex Analytics to production.

## Options at a glance

| Option | Best for | Monthly cost | Setup time | Walkthrough |
|--------|----------|--------------|------------|-------|
| **Railway** | Managed PaaS, no sysadmin work | ~$25-45 | ~2.5 hours | [RAILWAY-DEPLOY-WALKTHROUGH.md](../RAILWAY-DEPLOY-WALKTHROUGH.md) |
| **Cloudflare + Hetzner** | Cheapest; reuse an existing Cloudflare-managed domain | ~$7.50 | ~3 hours | [FIRST-DEPLOY-WALKTHROUGH.md](../FIRST-DEPLOY-WALKTHROUGH.md) |

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

## Cloudflare + Hetzner — production deploy (current canonical path)

The canonical, end-to-end production recipe is the single-subdomain plan
(`app.versatexanalytics.com` serving SPA + API + admin from the same
origin via Cloudflare Tunnel). Read these in order:

1. [PRODUCTION-DEPLOY-PLAN.md](PRODUCTION-DEPLOY-PLAN.md) — **Start here.** The strategic plan: architecture, apex-safety pre-flight, phases at a glance.
2. [FIRST-DEPLOY-WALKTHROUGH.md](../FIRST-DEPLOY-WALKTHROUGH.md) — **First-time setup.** Step-by-step VPS provision → tunnel → Access policies → `.env` assembly → first bring-up → edge rules. ~3 hours end-to-end, checkpointed for pauses. (Lives one level up in `docs/` for top-level discoverability.)
3. [DEPLOY-PLAYBOOK.md](DEPLOY-PLAYBOOK.md) — Day-to-day runbooks: deploy, rollback, migration safety, secret classification, common-failure diagnoses.
4. [MONITORING.md](MONITORING.md) — Uptime Kuma + external probe + Cloudflare signals. Probe definitions, alert routing, weekly metrics to watch.
5. [CLOUDFLARE-EDGE.md](CLOUDFLARE-EDGE.md) — Cache Rules, WAF, Rate-Limiting, SSL/TLS mode. Copy-paste-ready expressions with host-scoping clauses.
6. [BACKUPS-AND-MEDIA.md](BACKUPS-AND-MEDIA.md) — Postgres backups to R2, media file persistence, restore procedure.

### Supporting references (deep-dive / historical)

- [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md) — Older two-subdomain recipe (`app.*` + `api.*`). Superseded by PRODUCTION-DEPLOY-PLAN.md for new deployments; some sections (VPS hardening §1–§4, secret generation §5) are still referenced by the current plan.
- [CLOUDFLARE-DNS.md](CLOUDFLARE-DNS.md) — DNS record patterns alongside an existing apex site.
- [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md) — Zero-trust tunnel reference.
- [CLOUDFLARE-PAGES.md](CLOUDFLARE-PAGES.md) — Frontend-on-Pages alternative. Not used by the current plan (frontend ships as a container on the VPS for same-origin simplicity); documented for the future case where edge-caching the SPA outweighs architectural simplicity.

## Railway documents

Read the walkthrough first; the older RAILWAY docs pre-date the accuracy-audit deploy-prep work and are kept as historical reference only.

1. [RAILWAY-DEPLOY-WALKTHROUGH.md](../RAILWAY-DEPLOY-WALKTHROUGH.md) — **Start here.** Current walkthrough aligned with the post-audit repo state: project creation, Postgres + Redis + pgvector, backend/celery/frontend services, custom domains, Cloudflare proxy layer.
2. [RAILWAY.md](RAILWAY.md) — Pre-audit reference guide. Deprecated; superseded by the walkthrough above.
3. [RAILWAY-STEP-BY-STEP.md](RAILWAY-STEP-BY-STEP.md) — Pre-audit first-time walkthrough. Deprecated; useful for Railway concepts but specific steps may drift from current state.
