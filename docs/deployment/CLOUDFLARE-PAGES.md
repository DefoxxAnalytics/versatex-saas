# Cloudflare Pages Deployment (Frontend)

Deploy the React/Vite frontend on Cloudflare Pages. Free tier: unlimited bandwidth, unlimited static requests, 500 builds/month.

## Prerequisites

- Cloudflare account (the same one managing `versatexanalytics.com`).
- GitHub repo, with Cloudflare granted access during setup.
- Backend already deployed at `api.versatexanalytics.com` (see [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md)).

## Create the Pages project

1. Cloudflare dashboard → **Workers & Pages** → **Create application** → **Pages** tab → **Connect to Git**.
2. Authorize Cloudflare to access GitHub → select the repo.
3. Set up builds and deployments:

| Field | Value |
|-------|-------|
| Production branch | `master` |
| Framework preset | `None` |
| Build command | `cd frontend && corepack enable && pnpm install --frozen-lockfile && pnpm build` |
| Build output directory | `frontend/dist` |
| Root directory | (leave empty) |

Why **None** instead of the Vite preset? The Vite preset assumes the project is at the repo root. This is a monorepo with the frontend under `frontend/`, so the preset's defaults misalign.

4. **Environment variables** (production) — these are baked into the build:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://api.versatexanalytics.com/api` |
| `VITE_APP_TITLE` | `Versatex Analytics` |
| `VITE_APP_LOGO` | `/vtx_logo2.png` |
| `NODE_VERSION` | `20` |

5. **Save and Deploy**. First build takes ~3-5 minutes.

## Custom domain

1. Pages project → **Custom domains** → **Set up a custom domain**.
2. Enter `app.versatexanalytics.com`.
3. Cloudflare creates the CNAME in your DNS zone automatically and provisions TLS via Universal SSL.

The marketing site on the apex domain is unaffected — it's a separate DNS record.

## SPA fallback

React Router / Wouter need unknown paths to serve `index.html`. **Cloudflare Pages does not do this automatically** — a `_redirects` file in the build output is required.

This repo ships [`frontend/public/_redirects`](../../frontend/public/_redirects):

```
/*    /index.html   200
```

Vite copies `public/` into `dist/` during `pnpm build`, so the file lands at the Pages output root automatically. If deep links start 404-ing, check that `frontend/dist/_redirects` exists after the build.

## Environment variable gotcha

Vite env vars are **build-time**, not runtime. Changing `VITE_API_URL` in the Pages dashboard requires a **retry deployment** (Pages → Deployments → `...` → **Retry deployment**) or a new commit. The change doesn't propagate to already-built deployments.

## pnpm version

The repo uses pnpm. Cloudflare Pages supports pnpm if you either:

1. Keep `"packageManager": "pnpm@<version>"` in `frontend/package.json` (already present), **or**
2. Prefix the build with `corepack enable` (done in the build command above).

If builds fail with `pnpm: command not found`, that's why.

## Preview deployments

Every pull request gets a preview URL at `<hash>.<project>.pages.dev`. These are publicly reachable by default. To gate them behind Cloudflare Access (free tier: 50 users):

Pages project → **Settings** → **Preview deployments** → **Access policy** → add an email allowlist.

## CORS from the backend

The Django backend must accept requests from `https://app.versatexanalytics.com`. Confirm in `.env`:

```env
CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com
CSRF_TRUSTED_ORIGINS=https://app.versatexanalytics.com
```

Preview URLs (`*.pages.dev`) will hit CORS errors unless added explicitly. For routine development, use a staging backend and keep production CORS strict. For one-off testing:

```env
CORS_ALLOWED_ORIGINS=https://app.versatexanalytics.com,https://<preview>.pages.dev
```

## Verification

```bash
# Cert + HTTP/2
curl -I https://app.versatexanalytics.com

# Routes to the Vite bundle
curl -s https://app.versatexanalytics.com | grep -i 'vite\|versatex'

# Deep link does not 404
curl -I https://app.versatexanalytics.com/p2p-cycle
# Expect: 200
```

Open the site in a browser, log in, and confirm API calls to `api.versatexanalytics.com` succeed (DevTools → Network, no CORS errors).

## Rollback

Pages → Deployments → find the previous good deployment → **...** → **Rollback to this deployment**. Takes ~10 seconds.

## Cost notes

Free tier limits at time of writing:

- 500 builds per month (~16 per day). Busy PR activity can blow through this on active branches. Upgrade to $20/mo Pages Pro if needed.
- Unlimited bandwidth, unlimited requests on the free tier.
- 100 custom domains per project.

## Links

- Cloudflare Pages — https://developers.cloudflare.com/pages/
- Vite env vars — https://vitejs.dev/guide/env-and-mode.html
- Pages build configuration — https://developers.cloudflare.com/pages/configuration/build-configuration/
