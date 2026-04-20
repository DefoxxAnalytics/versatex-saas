# Cloudflare Tunnel Setup

Cloudflare Tunnel exposes services on the Hetzner VPS without opening any public ports. A `cloudflared` daemon dials outbound to Cloudflare and multiplexes inbound traffic back to local containers.

## Why Tunnel

| Approach | Open ports | Origin IP hidden | Cost |
|----------|------------|------------------|------|
| A record + Caddy on VPS | 80, 443 | No (visible via `dig`) | $0 but more config |
| **Cloudflare Tunnel** | **None** | **Yes** | **$0** |

Tunnel also removes the need to deal with Let's Encrypt rate limits, origin certs, or ACME port-80 challenges.

## Prerequisites

- Cloudflare account with `versatexanalytics.com` managed.
- Zero Trust enabled (free tier; Cloudflare prompts on first tunnel).
- Hetzner VPS already running Docker (see [CLOUDFLARE-HETZNER.md](CLOUDFLARE-HETZNER.md)).

## Mode 1: Dashboard-managed (recommended for first setup)

The dashboard stores the tunnel config; the VPS runs a stateless `cloudflared` container authenticated with a token. Easiest path.

### Create the tunnel

1. Cloudflare dashboard → top-right account menu → **Zero Trust**.
2. Left sidebar → **Networks** → **Tunnels** → **Create a tunnel**.
3. Connector type: **Cloudflared** → **Next**.
4. Name: `versatex-prod` → **Save tunnel**.
5. On the **Install and run a connector** screen, locate the token in the install command. It's the base64 string after `--token` in `cloudflared service install <token>`. Copy just the token value.

### Add the connector to docker-compose

Create `docker-compose.tunnel.yml` in the repo root:

```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: analytics-cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARED_TOKEN}
    depends_on:
      - backend
    networks:
      - default
```

Add the token to `.env`:

```env
CLOUDFLARED_TOKEN=<paste-token-here>
```

Start the stack with all three compose files:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.tunnel.yml \
  up -d
```

Within ~30 seconds the tunnel shows as **HEALTHY** in the Zero Trust dashboard.

### Map public hostnames

Back in the tunnel config page → **Public Hostnames** tab → **Add a public hostname**.

API:

| Field | Value |
|-------|-------|
| Subdomain | `api` |
| Domain | `versatexanalytics.com` |
| Path | (leave empty) |
| Type | `HTTP` |
| URL | `backend:8000` |

Save. Cloudflare creates the `api` CNAME automatically and starts routing.

Optional — Flower (Celery monitoring):

| Field | Value |
|-------|-------|
| Subdomain | `flower` |
| Domain | `versatexanalytics.com` |
| Type | `HTTP` |
| URL | `flower:5555` |

Flower already has HTTP basic auth (`FLOWER_BASIC_AUTH` in docker-compose), so exposing it is safe once the password is strong. Better: put it behind Cloudflare Access for an extra gate (Zero Trust → **Access** → **Applications** → add self-hosted).

### Why `backend:8000`, not `localhost:8000`?

`cloudflared` runs as a container on the same Docker network as `backend`. Service discovery uses container names. `localhost` inside the `cloudflared` container resolves to the cloudflared container itself, not the backend.

## Mode 2: config.yml (version-controlled)

If you want the tunnel config in git, use file mode.

### Create the tunnel via CLI

On your local machine (not the VPS):

```bash
# Install cloudflared locally
brew install cloudflared        # macOS
# or: sudo apt install cloudflared  (after adding Cloudflare's apt repo)
# or: winget install cloudflare.cloudflared  (Windows)

cloudflared tunnel login
cloudflared tunnel create versatex-prod
```

This writes `~/.cloudflared/<uuid>.json` with the tunnel credentials. Copy to the VPS at `./cloudflared/credentials.json`.

### Write the config

Create `cloudflared/config.yml` in the repo root:

```yaml
tunnel: <tunnel-uuid>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: api.versatexanalytics.com
    service: http://backend:8000
  - hostname: flower.versatexanalytics.com
    service: http://flower:5555
  - service: http_status:404
```

Route DNS:

```bash
cloudflared tunnel route dns versatex-prod api.versatexanalytics.com
cloudflared tunnel route dns versatex-prod flower.versatexanalytics.com
```

### docker-compose entry

```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: analytics-cloudflared
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflared:/etc/cloudflared:ro
    depends_on:
      - backend
    networks:
      - default
```

Do **not** commit `cloudflared/credentials.json`. Add to `.gitignore`:

```
cloudflared/credentials.json
```

## Verification

```bash
# Tunnel is up
docker compose logs cloudflared --tail=20
# Expect: "Registered tunnel connection" lines

# DNS resolves through Cloudflare
dig +short api.versatexanalytics.com
# Expect: Cloudflare IPs (104.21.* or 172.67.*)

# End-to-end
curl -I https://api.versatexanalytics.com/admin/login/
# Expect: HTTP/2 200 or 302
```

## Troubleshooting

### `Error 1033: Argo Tunnel error`

The `cloudflared` container isn't connected to Cloudflare. Logs show auth failures (bad token) or network errors.

### `502 Bad Gateway`

Tunnel is up, but the origin service isn't responding. Test from inside the cloudflared container:

```bash
docker compose exec cloudflared wget -qO- http://backend:8000/admin/login/
```

If this fails, `backend` isn't on the same Docker network or isn't running. Verify with `docker compose ps`.

### `Error 1016: Origin DNS error`

The public hostname's service URL is wrong. Must be `http://<service-name>:<port>` where `<service-name>` matches a `services:` entry in docker-compose (e.g. `backend`, `flower`).

### Tunnel shows DEGRADED briefly

Usually transient — Cloudflare maintains multiple edge connections and one can drop and reconnect. Investigate if it stays degraded for more than 5 minutes.

### Changing hostnames

Dashboard mode: edit the public hostname in the Zero Trust UI, changes apply immediately.
Config.yml mode: edit `cloudflared/config.yml`, then restart the container: `docker compose restart cloudflared`.

## Links

- Cloudflare Tunnel docs — https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- `cloudflared` Docker image — https://hub.docker.com/r/cloudflare/cloudflared
- Cloudflare Access — https://developers.cloudflare.com/cloudflare-one/applications/
