# Monitoring

Uptime, health, and cost observability for the production deployment.

## 1. Coverage map

Three independent probe sources, chosen so a single failure never
silences all of them.

| Source | Where it runs | Catches | Catches if VPS is down? |
|---|---|---|---|
| **Uptime Kuma** | On the VPS (`uptime-kuma` container) | App-layer health (DB, Redis, login), cert expiry, response-time spikes | No — silenced by the very outage it should report |
| **External probe** (Healthchecks.io free / BetterStack free) | 3rd-party infra, outside our VPS | Full-VPS or Cloudflare-tunnel outages | **Yes** — primary signal for "everything's on fire" |
| **Cloudflare passive** (Zero Trust tunnel health, Analytics, Security → Events) | Cloudflare edge | Tunnel status, WAF event volume, cache hit ratio | **Yes** — but lags by 60s |

**Minimum viable setup:** all three. Skipping the external probe is a
common mistake; the VPS-hosted Uptime Kuma has a blind spot for its own
host failure.

---

## 2. Uptime Kuma setup

### First boot

After the monitoring overlay is up (Phase 5c + Phase 11), reach Kuma via
`https://monitor.versatexanalytics.com/` — gated by the Cloudflare Access
policy provisioned in Phase 11.

1. First visit prompts for admin account creation. Use a strong
   password; store in 1Password. This is Kuma's own auth layer on top of
   Cloudflare Access (belt-and-suspenders — if you ever loosen CF Access,
   Kuma's own auth still protects it).
2. Settings → General → Timezone: UTC.
3. Settings → Notifications → New: **Ntfy** (or whichever channel matches
   `ALERT_WEBHOOK_URL` in `.env`). Use a random topic name as a shared
   secret — see §4.
4. Settings → Notifications → New: **SMTP** using the Resend creds from
   `.env` (`EMAIL_HOST=smtp.resend.com`, port 587, TLS). From address:
   `alerts@versatexanalytics.com`. Two recipients (primary + backup).

### Probe definitions

Create each of these as an individual monitor. All probes retry twice
before firing; interval 60 s unless noted.

| # | Name | Type | Target | Expectation | Notes |
|---|---|---|---|---|---|
| 1 | Frontend root | HTTP(s) | `https://app.versatexanalytics.com/` | status 200, TLS valid, within 5 s | TLS cert check is zone-managed (Cloudflare); alerts ~30 d before expiry |
| 2 | Backend readiness | HTTP(s) - keyword | `https://app.versatexanalytics.com/api/health/` | status 200 AND body contains `"db":"ok"` AND `"redis":"ok"` | Primary app-layer probe |
| 3 | Admin login gate | HTTP(s) | `https://app.versatexanalytics.com/${ADMIN_URL}login/` | status 302 (redirect to CF Access), within 5 s | Catches Access-policy misconfig |
| 4 | Postgres TCP | TCP Port | `db:5432` | connection opens | Internal probe, Docker DNS |
| 5 | Redis TCP | TCP Port | `redis:6379` | connection opens | Internal probe |
| 6 | Flower availability | HTTP(s) - basic auth | `http://flower:5555/healthcheck` | status 200 | Optional; celery monitoring dashboard |

Probes 4 + 5 use Docker-internal hostnames because Kuma runs in the
same compose network. That's intentional: it means Kuma sees the real
intra-cluster state, not the CF-edge view.

### Status page (optional)

Kuma's built-in status page is suitable for exposing a public
"is Versatex up right now?" URL later. Skip at v1; revisit when you have
enough users to justify a public stats page.

---

## 3. External probe

Needed because Uptime Kuma is co-located with the thing it monitors.
Full VPS outage (data-center loss, Hetzner network incident, accidental
`docker compose down`) silences every probe in §2.

### Healthchecks.io (recommended — free forever tier fits this use case)

1. Sign up → create a new check named `versatex-app-health`.
2. Schedule: expect a ping every **5 minutes**, grace 2 minutes.
3. Copy the check URL.
4. **But wait** — Healthchecks.io's primary model is passive ("your
   service pings us"). For active probing ("please hit my URL and
   confirm it responds"), use the notification channel instead:
5. On the check, add a **Read-Only GET Webhook** → enter
   `https://app.versatexanalytics.com/api/health/` → expected status
   `200`. The service pings our URL on the schedule and marks the check
   down if the URL fails.

Alternative: **BetterStack free tier** — gives proactive uptime checks
out of the box (10 monitors free). Simpler setup; UI is nicer; same
reliability class.

### Cron-free alternative

If the 3rd-party signup feels like yet-another-account, a DIY option:
run the external probe as a GitHub Actions workflow cron. Add a
`.github/workflows/uptime-probe.yml` that runs every 5 min and curls
`/api/health/`. Failure → workflow fails → GitHub emails you. Free,
no extra account.

This isn't documented as the primary path because GitHub's scheduled
workflows run on a best-effort basis and can skew by minutes. Good
enough for a safety-net signal, not suitable as the primary probe.

---

## 4. Alert routing — ntfy.sh

Push notifications to your phone + email fallback.

### Setup

1. Pick a random topic name: `versatex-alerts-<8-hex-chars>`. Treat it
   as a shared secret — anyone who knows the topic can read AND post
   messages on it.
2. Install the **ntfy** mobile app (iOS / Android). Subscribe to the
   topic.
3. Add the topic URL to `.env` as
   `COST_ALERT_WEBHOOK_URL=https://ntfy.sh/<topic>` and
   `ALERT_WEBHOOK_URL=https://ntfy.sh/<topic>` (can reuse).
4. In Kuma (Settings → Notifications), add an Ntfy channel with the same
   topic.
5. Push test: `curl -d "test alert" https://ntfy.sh/<topic>`. Expect
   phone notification within 5 s.

### Email fallback

1. Resend free tier (already set up for Django `send_mail` — re-use).
2. In Kuma (Settings → Notifications), add an SMTP channel pointing at
   `smtp.resend.com:587`.
3. Recipients: primary (you) + backup (trusted colleague or personal
   email alias).

### Alert severity tiers

Kuma doesn't differentiate severity out of the box. Apply this
convention manually in notification-message templates:

| Severity | Meaning | Channels |
|---|---|---|
| **P1 — Down** | App unreachable, DB or Redis offline | ntfy + SMS (pager tier — add Twilio if you need one, optional) |
| **P2 — Degraded** | p95 latency >5s, backup stale, DB >90% full | ntfy + email |
| **P3 — Advisory** | Single probe flapping, cost digest anomaly | email only |

v1: only ntfy + email. Pager-grade P1 escalation is a post-MVP addition.

---

## 5. Metrics to watch weekly

Spend 15 minutes each Monday reviewing. Early-warning for slow-moving
problems.

### Cloudflare Analytics (Zero Trust dashboard + Analytics)

- **Tunnel status:** should be HEALTHY. Any gap > 1 min = investigate.
- **Requests (24h):** baseline is stable for your user count. Sudden
  drops = outage we didn't catch. Sudden spikes = crawler / credential
  stuffing → check Security → Events.
- **Cache hit ratio** on `/assets/*` — target >80% after 1 week. Lower =
  cache rule misconfigured or aggressive cache-busting URLs.

### Cloudflare Security → Events

- WAF events volume: baseline ~10–50/day from script-kiddie scans.
- False positive count: if legit users hit WAF blocks, either whitelist
  or tune Bot Fight Mode.

### Kuma dashboard

- Probe response times p95 over 7 days. Trend-watch:
  - Backend readiness p95 creeping past 2 s = DB or Redis getting slow.
  - Frontend root p95 stable ≤ 1 s except during deploys.

### VPS host

Run weekly:
```bash
ssh deploy@<vps-ip>
./scripts/capacity-check.sh
df -h
docker stats --no-stream
```

- Disk growth: steady ~100 MB/day is normal. Sudden +1GB/day = check
  `/var/lib/docker/volumes/` and `/var/lib/docker/containers/`.
- Container memory: none should sustain >80% of its limit.

### Backups

- `rclone ls r2:versatex-backups/postgres/ | tail -5` — newest file ≤24h
  old.
- File size growth trend: grows linearly with DB size. A sudden *drop*
  in dump size vs yesterday = dump truncated / DB partially deleted.

### LLM cost digest (6:00 UTC daily ntfy push)

- Baseline established after 1 week.
- Any single day > 2× average → investigate which `request_type`
  exploded. `LLMRequestLog` has per-row cost + type for drilling down.

### Scheduled Reports (v3.1, beat-driven)

- **Hourly :00 UTC** — `process_scheduled_reports` should appear in
  `docker compose logs celery` at least once per hour. Silent failure
  mode: UI-scheduled Reports never run.
- **Daily 01:00 UTC** — `cleanup_expired_reports` purges stale
  `ReportFile` rows. Verify weekly with
  `docker compose logs --since 168h celery | grep cleanup_expired_reports`.
- These tasks ride the same celery-beat container as the AI batch jobs;
  if those go quiet, both pipelines are down. See
  [CLOUDFLARE-HETZNER.md § Known gaps](CLOUDFLARE-HETZNER.md) for the
  beat-service caveat (compose default doesn't run beat — production
  override does).

---

## 6. Alerting operations

### Silence a false positive

Cause: a probe flaps because of a transient network blip, not a real
outage. Fix: Kuma → the monitor → Pause (timed 2h default). Resume
after the underlying cause is understood.

Do NOT: disable the probe permanently. You'll forget it's off and a
real outage goes silent.

### Acknowledge an alert

Kuma sends a push; you're on it. No formal "ack" inside Kuma, but:
1. Tap the ntfy notification → opens the Kuma dashboard.
2. Leave a status note in the monitor's history: Kuma → monitor →
   History → Add note. Short: "2026-05-01 02:15 — p95 spike during
   `batch_generate_insights`; expected duration ~30 min."

### Run a test alert

Confirm the alert chain still works, especially after rotating tokens:
```bash
curl -d "test alert from $(hostname) at $(date -u)" \
  -H "Title: Versatex monitoring test" \
  https://ntfy.sh/<topic>
```

Expect phone notification within 5 s. If it doesn't arrive, check:
1. Phone ntfy app subscribed to correct topic
2. Do Not Disturb disabled on phone
3. ntfy.sh itself is up (`curl -sI https://ntfy.sh/` → 200)

---

## 7. What you're NOT monitoring (yet)

Explicit scope limits for v1.

- **Per-endpoint latency breakdowns.** Kuma gives aggregate; no
  per-route profiling. If you need it, add `django-silk` (P2 roadmap).
- **Error rates by endpoint.** Django logs go to stdout → json-file
  rotation → no aggregation. If you need it, ship logs to Grafana Loki /
  Better Stack (P1 roadmap).
- **User-journey synthetic tests.** "Simulate a login → dashboard →
  chart render flow every 5 min" — Playwright-as-a-probe, not yet wired.
- **APM (Sentry / DataDog).** No crash aggregation or performance
  traces. P1 roadmap item.

When Uptime Kuma alone starts to feel thin, add these in order:

1. Sentry free tier for error aggregation (single `pip install` + DSN).
2. Grafana Cloud free tier + Prometheus exporters for
   container/postgres metrics.
3. Playwright synthetic tests as a 6th Kuma monitor.

---

## Cross-references

- [DEPLOY-PLAYBOOK.md](DEPLOY-PLAYBOOK.md) — what to do when an alert
  fires (§3 Rollback, §8 Common failure modes).
- [CLOUDFLARE-EDGE.md](CLOUDFLARE-EDGE.md) — WAF/Cache rules that
  generate the events in §5.
- [PRODUCTION-DEPLOY-PLAN.md](PRODUCTION-DEPLOY-PLAN.md) §11 —
  one-time Kuma provisioning happens there.
- [docker-compose.monitoring.yml](../../docker-compose.monitoring.yml) —
  the Kuma service definition.
