# Cloudflare DNS for App Subdomains

How to add subdomains for Versatex Analytics alongside an existing site on the apex domain, without breaking the existing site.

## Context

You already have `versatexanalytics.com` (or equivalent) on Cloudflare serving a marketing site. We need to add:

- `app.versatexanalytics.com` — frontend on Cloudflare Pages
- `api.versatexanalytics.com` — backend via Cloudflare Tunnel

Subdomains are **independent DNS records** from the apex. The marketing site keeps serving from `versatexanalytics.com` (and `www.*`). Nothing about those records needs to change.

## Records to add

Open Cloudflare dashboard → `versatexanalytics.com` → **DNS** → **Records**.

| Type  | Name  | Content                          | Proxy status | TTL  |
|-------|-------|----------------------------------|--------------|------|
| CNAME | `app` | `<your-project>.pages.dev`       | Proxied      | Auto |
| CNAME | `api` | `<tunnel-id>.cfargotunnel.com`   | Proxied      | Auto |

Notes:

- The `api` CNAME is created **automatically** when you add a public hostname in the Cloudflare Tunnel dashboard. Don't create it by hand first — Cloudflare rejects the duplicate.
- The `app` CNAME is created **automatically** when you add a custom domain in the Cloudflare Pages project settings.
- Both records should stay **proxied** (orange cloud). That's what gives you Cloudflare's free TLS, DDoS protection, and caching.

## Why not an A record for the API subdomain?

You could point `api.versatexanalytics.com` directly at the Hetzner IPv4 via an A record. Two reasons not to:

1. **Exposes the origin IP.** Cloudflare's DDoS protection is bypassable if the attacker knows the origin IP.
2. **Requires opening firewall ports (80/443).** Tunnel keeps the VPS firewall at "SSH only".

Keep the CNAME through Tunnel.

## TLS certificates

Cloudflare's **Universal SSL** auto-issues a cert for every hostname in the zone, including new subdomains, within a few minutes of the record being created. No manual cert work.

End-to-end TLS (Cloudflare → origin encrypted with a real cert) is handled by Tunnel automatically. If you ever switch to a direct A record, generate a Cloudflare **Origin Certificate** (15-year self-signed, trusted only by Cloudflare) and terminate TLS on the origin with Caddy or nginx.

## Gotchas

### Existing wildcard record

If your zone already has `*.versatexanalytics.com` pointing somewhere (common for preview environments), an explicit `app` or `api` record **overrides** the wildcard for that name. That's what you want. Verify:

```bash
dig +short app.versatexanalytics.com
# Expect Cloudflare IPs (104.21.* or 172.67.*), not the wildcard target.
```

### CAA records

If the zone has a CAA record restricting which CAs can issue certs, Cloudflare's issuers (`pki.goog`, `letsencrypt.org`, `digicert.com`, `ssl.com`) must be in the allow-list or Universal SSL will fail. Check under **DNS** → **Records**, filter by type `CAA`. If present, add Cloudflare's CAs or remove the restriction (Cloudflare handles CAA implicitly for proxied records).

### MX records are unaffected

The apex `MX` records control mail delivery to `anything@versatexanalytics.com`. Adding `app` / `api` CNAMEs does not touch mail routing.

### Sending email *from* the api subdomain

If Django password-reset emails use `noreply@api.versatexanalytics.com` as the From address, you'll need a separate TXT SPF record on `api` and DKIM/DMARC configured at your email provider. Outside the scope of this doc.

## Verification

```bash
# Should return Cloudflare IPs
dig +short app.versatexanalytics.com
dig +short api.versatexanalytics.com

# TLS cert issued for both
curl -vI https://app.versatexanalytics.com 2>&1 | grep -i 'subject\|issuer'
curl -vI https://api.versatexanalytics.com 2>&1 | grep -i 'subject\|issuer'
```

If `dig` returns the origin IP instead of Cloudflare IPs, the proxy is off (grey cloud). Click the cloud icon on the record to turn it on.

## Rollback

Removing either record does not affect the marketing site on the apex.

- `app.*`: Cloudflare Pages → project → **Custom domains** → remove `app.versatexanalytics.com`. Cloudflare removes the CNAME.
- `api.*`: Cloudflare Tunnel → tunnel → **Public Hostnames** → remove `api.versatexanalytics.com`. Cloudflare removes the CNAME.
