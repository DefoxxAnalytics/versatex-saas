# Cloudflare Edge Rules

Cache, WAF, and rate-limit rules applied at the Cloudflare zone level
after the tunnel is live.

## Prerequisites

Before touching anything in this doc:

1. The Cloudflare Tunnel is up per
   [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md); the app resolves at
   `https://app.versatexanalytics.com/`.
2. The apex pre-flight inventory (baseline DNS / SSL / rule lists,
   per [PRODUCTION-DEPLOY-PLAN.md §Apex-safety pre-flight](PRODUCTION-DEPLOY-PLAN.md#apex-safety-pre-flight-do-before-touching-cloudflare))
   is captured. Every change below is applied on top of that baseline.
3. The marketing site on `versatexanalytics.com` is known-good at its
   own origin; you have a way to revert any zone-wide setting in <60 s.

## The host-scoping rule (read first)

**The zone `versatexanalytics.com` is shared between the marketing
apex and the app subdomain.** A handful of settings are genuinely
zone-wide — they can't be scoped per-hostname. All others **must** be
scoped by adding the expression:

```
(http.host eq "app.versatexanalytics.com")
```

AND-ed with every other condition. Skipping this clause = the rule
applies to the marketing site too. The single most common way to
accidentally break the apex.

| Setting class | Zone-wide? | Notes |
|---|---|---|
| Cache Rules | No — host-scoped | Always include host clause |
| Rate-Limiting Rules | No — host-scoped | Always include host clause |
| WAF Custom Rules | No — host-scoped | Always include host clause |
| WAF Managed Ruleset | Zone-wide | Zone default; can override per-rule if needed |
| SSL/TLS mode | **Zone-wide** | Test marketing origin TLS before switching |
| Always Use HTTPS | **Zone-wide** | Verify marketing doesn't intentionally serve HTTP anywhere |
| HSTS | **Zone-wide** | See Phase 8 pre-flight before flipping |
| Bot Fight Mode | **Zone-wide** | Free; watch for false-positives on marketing-site crawlers |

---

## 1. SSL/TLS mode — Full (strict)

**Setting:** Cloudflare Dashboard → SSL/TLS → Overview → **Full (strict)**.

**Why this works with a tunnel:** `cloudflared` terminates TLS at the
Cloudflare edge with a Cloudflare-issued certificate. The edge validates
that certificate, which is always valid by construction. No origin
certificate to manage on the VPS; no renewal cron; no expiry incidents.

**Why it's safe for marketing too:** only safe if the marketing origin
already serves a valid (non-self-signed) TLS cert on port 443. If
marketing is on Cloudflare Pages / Vercel / a known PaaS, this is
automatic. If marketing is on a custom origin, test before switching:

```bash
curl -Iv --resolve versatexanalytics.com:443:<marketing-origin-ip> \
  https://versatexanalytics.com/
```

If the cert is self-signed or the origin only speaks HTTP, **do not**
switch to Full (strict). Keep the zone on `Full` (lax); the tunnel leg
still terminates TLS correctly either way.

---

## 2. Cache Rules

Applied in Cloudflare Dashboard → Rules → Cache Rules. Order matters —
first-matching rule wins. Create in the order listed.

### Rule 1 — Cache `/assets/*` aggressively

```
Name:        versatex-app — cache static assets
Expression:  (http.host eq "app.versatexanalytics.com" and starts_with(http.request.uri.path, "/assets/"))
Action:      Eligible for cache
Edge TTL:    1 year (31536000 seconds)
Browser TTL: 1 year
Bypass on:   Cache-Control request header
```

**Why:** Vite emits hashed filenames under `/assets/` (e.g.
`/assets/index-BHU_ivCV.js`). Content is immutable for the life of that
hash. Caching at the edge for a year means every user globally hits a
Cloudflare PoP for static assets — no origin request.

### Rule 2 — Bypass cache on HTML, API, admin, media

```
Name:        versatex-app — bypass cache on dynamic
Expression:  (http.host eq "app.versatexanalytics.com" and (
               http.request.uri.path in {"/" "/index.html"}
               or starts_with(http.request.uri.path, "/api/")
               or starts_with(http.request.uri.path, "/admin/")
               or starts_with(http.request.uri.path, "/media/")
             ))
Action:      Bypass cache
```

**Why:** index.html must always re-fetch so users get the latest asset
hashes. `/api/` and `/admin/` are by definition dynamic. `/media/`
serves user uploads — cache invalidation on upload would be a whole
separate problem we don't want.

### Fingerprinted-extension addendum (optional, skip at v1)

If telemetry shows users downloading `.woff2` / `.png` / `.jpg` outside
`/assets/`, add a third rule for `http.request.uri.path matches
"\\.(woff2?|png|jpe?g|gif|svg|ico)$"` with the same 1y TTL. Skip at v1
because Vite bundles fonts + images under `/assets/` already.

---

## 3. WAF — Managed Ruleset + Bot Fight Mode

### Cloudflare Managed Ruleset (zone-wide, free)

**Setting:** Security → WAF → Managed Rules → "Cloudflare Managed
Ruleset" → Deploy.

Covers known CVEs, common injection patterns, credential-stuffing
signatures. Free tier is good enough for v1.

**Caveat:** This is zone-wide by default. If the marketing site is
CMS-based (WordPress-style plugin admin URLs), Managed Ruleset may
block a legitimate admin path. Run in "Log only" mode for the first 24
hours, check Security → Events for false positives, then flip to
"Block" if clean.

### Bot Fight Mode (zone-wide, free)

**Setting:** Security → Bots → "Bot Fight Mode" → On.

Stops most automated scraping and low-sophistication credential
stuffing. Free. Watch for false positives on legitimate API consumers
(if the Versatex app ever exposes a public read-only API, those
consumers need a `cf-access-client-id` / `cf-access-client-secret`
token to bypass Bot Fight Mode).

---

## 4. Rate-Limiting — login paths

Applied in Cloudflare Dashboard → Security → WAF → Rate-Limiting Rules.

```
Name:        versatex-app — login throttle
Expression:  (http.host eq "app.versatexanalytics.com" and (
               starts_with(http.request.uri.path, "/api/v1/auth/login/")
               or starts_with(http.request.uri.path, "/${ADMIN_URL}login")
             ))
Rate:        10 requests per 10 minutes per IP
Action:      Block
Duration:    10 minutes
```

**Replace `${ADMIN_URL}`** with the literal obscured path from `.env`
(e.g. `manage-3f2b1a7c/`). The rule expression must use the actual
value, not a variable.

**Why 10/10min:** Django's failed-login lockout (in
`apps/authentication/utils.py`) kicks in at 5 attempts per user per 30
min. Cloudflare's rate limit catches IP-level brute force *before*
Django sees it, preserving DB and CPU. 10 legitimate attempts in 10
min is still plausible (users with typo-prone passwords); 11 = nearly
always abuse.

**Watch for:** corporate users behind a shared NAT. If false positives
appear, raise to 20/10min.

---

## 5. Verification

After applying all rules:

### Cache working

```bash
# First request — cold cache.
curl -sI https://app.versatexanalytics.com/assets/index-<hash>.js \
  | grep -i cf-cache-status
# Expected: cf-cache-status: MISS or EXPIRED

# Second request within 60s.
curl -sI https://app.versatexanalytics.com/assets/index-<hash>.js \
  | grep -i cf-cache-status
# Expected: cf-cache-status: HIT
```

### API bypassing cache

```bash
for i in 1 2 3; do
  curl -sI https://app.versatexanalytics.com/api/health/ \
    | grep -i cf-cache-status
done
# Expected: cf-cache-status: BYPASS (all three)
```

### Rate limit firing

```bash
# 11 rapid-fire login attempts, expect the 11th to block with 429.
for i in $(seq 1 11); do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST https://app.versatexanalytics.com/api/v1/auth/login/ \
    -d '{"username":"fake","password":"fake"}' \
    -H 'Content-Type: application/json')
  echo "Attempt $i: $code"
done
# Expected: first 10 → 400/401 (Django responding), 11th → 429 (Cloudflare blocked)
```

Wait 10 minutes for the rate limit to clear before real testing.

### WAF events visible

Make one request with an obviously-malicious payload to trigger WAF:

```bash
curl -s "https://app.versatexanalytics.com/?id=<script>alert(1)</script>" \
  -o /dev/null -w "%{http_code}\n"
# Expected: 403 or the request blocked by WAF
```

Then: Cloudflare Dashboard → Security → Events → expect the entry
within 60 s.

---

## 6. Post-apply apex regression

After every Cloudflare edge change, verify the marketing site still
works. From Phase 8 baseline:

```bash
curl -sI https://versatexanalytics.com/ > /tmp/apex-headers-now.txt
diff /tmp/apex-baseline-headers.txt /tmp/apex-headers-now.txt
```

Expected: zero relevant diff. Cloudflare may change `cf-ray` per
request (unique request ID) — that's fine.

In browser:
1. Load the marketing homepage.
2. Load one deep link (pricing, about, whatever exists).
3. If the marketing site has forms or external analytics, exercise one
   flow end-to-end.

If any of the above regresses: see §8 rollback.

---

## 7. Zone-wide tradeoffs checklist

Before flipping anything under SSL/TLS → Edge Certificates or Security →
Bots, consult this table. Any "**yes**" in the "Zone-wide?" column means
the change affects the marketing site too.

| Change | Zone-wide? | Pre-flight check | Rollback time |
|---|---|---|---|
| SSL/TLS mode → Full (strict) | yes | Marketing origin cert valid (§1) | <30 s (revert in UI) |
| Always Use HTTPS → On | yes | Marketing doesn't intentionally serve HTTP | <30 s |
| HSTS `includeSubDomains=true` | yes | **Irreversible for 1 year** from enable-date | 1 year (!) |
| HSTS `preload=true` | yes | Requires HSTS-preload.org submission; **only mostly reversible** | 6–12 weeks via removal submission |
| Bot Fight Mode → On | yes | Marketing crawlers (SEO tools) tolerated? | <30 s |
| Managed Ruleset → Block (from Log) | yes | 24h false-positive audit complete | <30 s |

**Default for v1:** enable SSL/TLS Full (strict) + Always Use HTTPS +
Managed Ruleset (Log-first-24h-then-Block) + Bot Fight Mode. Skip HSTS
preload until app has been stable >1 week and you're sure you'll never
need to serve HTTP on any `*.versatexanalytics.com` subdomain.

---

## 8. Rollback per-change

| Change | Rollback |
|---|---|
| Cache rule breaking an asset | Dashboard → Rules → Cache Rules → toggle off the rule. Applies in <30 s. |
| Rate limit false-positive | Dashboard → Security → WAF → Rate-Limiting → edit the rule to raise rate OR change action to "Log" / "Challenge". |
| WAF blocking legitimate requests | Dashboard → Security → Events → find the blocked event → "Add exception for this IP/URL". Or toggle the Managed Ruleset rule to "Log" only. |
| SSL/TLS mode regression on marketing | Dashboard → SSL/TLS → Overview → revert to previous mode. |
| Bot Fight Mode false positives | Dashboard → Security → Bots → Bot Fight Mode → Off. |

All reversible via the Cloudflare UI; none require a VPS touch.

---

## Cross-references

- [PRODUCTION-DEPLOY-PLAN.md](PRODUCTION-DEPLOY-PLAN.md) §Apex-safety
  pre-flight — capture baseline BEFORE making any zone-wide change.
- [CLOUDFLARE-DNS.md](CLOUDFLARE-DNS.md) — DNS records alongside the
  apex.
- [CLOUDFLARE-TUNNEL.md](CLOUDFLARE-TUNNEL.md) — tunnel setup that
  must be live before any of this matters.
- [DEPLOY-PLAYBOOK.md](DEPLOY-PLAYBOOK.md) §8 — runtime failure-mode
  diagnosis if an edge rule misfires in production.
- [MONITORING.md](MONITORING.md) §5 — weekly review of Cloudflare
  Analytics + Security → Events.
