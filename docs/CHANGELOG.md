# Versatex Analytics Changelog

Curated history of significant architectural decisions and the reasoning behind them. For full feature inventories at each release, see git log. This file documents the *why* — what motivated each change, what tradeoffs were accepted.

> **For Claude Code sessions:** This file is reference-only. Read it when investigating "why does the code work this way" or before changing a design that has historical context.

## v2.11 (2026-01-22) — Demo tenant support

**Why:** Superusers needed to distinguish demo orgs (containing seeded synthetic data) from real customer orgs at a glance, and data-governance actions needed to gate on the distinction.

**Key decisions:**
- Made `Organization.is_demo` a first-class `BooleanField`, not a derived flag — explicit field is queryable, indexable, and clearer in admin
- Three serializer paths because `OrganizationSwitcher` synthesizes `Organization` objects from memberships on one branch and hits `/auth/organizations/` on the other — simpler to add the field everywhere than re-architect the switcher
- Admin export ZIP action gated on `is_demo=True` only — no real-tenant data ever exports
- Drift-guard test added because admin import + admin export must round-trip; either side changing column order silently breaks restoration

## v2.10 (2026-01-15) — Versatex brand color scheme + demo data seeding

**Why (brand):** Customer onboarding required a brand-aligned theme option separate from the navy/classic options that targeted a different visual register.

**Key decisions:**
- Three-whitelist gotcha is intentional, not refactored away — TypeScript union, backend `ChoiceField`, runtime `saveSettingsToStorage` whitelist each serve as defense-in-depth gates. Loosening any one would silently accept invalid values from the other layers.
- Spend Distribution donut explicitly carved out — its red/yellow/green is **semantic risk tier**, not decoration. Brand palette would break the affordance.

**Why (seeding):** Customer demos kept getting blocked by manually-curated demo data drifting from current schema. Industry-specific profiles let customers see realistic data immediately.

**Key decisions:**
- Two commands instead of one (`seed_industry_data` + `seed_demo_data`) — base layer (suppliers, transactions) often regenerated independently of P2P layer
- `--seed` deterministic, `--wipe` idempotent — required for reliable smoke tests in CI
- Industry profiles in a separate file (`_industry_profiles.py`) — adding industries should be data-only changes, not code changes

## v2.9 (2026-01-08) — LLM-powered AI Insights enhancement

**Why:** Initial v2.6 ROI tracking proved insights were valuable but cost-prohibitive at scale. Optimization required.

**Key decisions:**
- Prompt caching primary lever (90% reduction on cached reads) — system prompts are stable; per-request data isolated to non-cached blocks
- Semantic cache 0.90 threshold chosen via cost/quality tradeoff testing — lower threshold returned semantically-close-but-wrong answers
- Tiered model selection (Haiku for simple queries) — 50% of insight types don't need Opus reasoning
- No silent fallback rule (now Convention §6) — users couldn't tell if they were seeing AI-enhanced or deterministic output, eroding trust
- Vector storage via pgvector inside Postgres rather than separate vector DB — operational simplicity beats specialized performance at current scale

## v2.8 (2025-12-18) — Senior management documentation

**Why:** Executive sponsors needed a non-technical introduction to the platform.

**Key decisions:**
- Generated PDF + PowerPoint via Python scripts (`generate_pdf.py`, `generate_pptx.py`) checked into `docs/` — repeatable, version-controlled, no separate design tool
- Screenshots auto-captured into `docs/screenshots/` — eliminates "the screenshot is stale" maintenance problem

## v2.7 (2025-12-10) — Production hardening

**Why:** Approaching first customer deployment; security audit identified missing CSP, headers, and standalone Nginx config.

**Key decisions:**
- Standalone `frontend/nginx/nginx.conf` mounted as volume in production override — config changes shippable without rebuilding the frontend image
- CSP added inline rather than via meta tag — server-enforced, browser-trusted
- Test mock fixes (65 errors) batched with hardening — don't ship security work alongside flaky tests

## v2.6 (2025-12-03) — Multi-organization users + AI Insights ROI tracking

**Why (multi-org):** Consultants and auditors needed cross-org access without separate accounts. Per-org role (admin in Org A, viewer in Org B) is the natural authorization model.

**Key decisions:**
- `UserOrganizationMembership` as many-to-many with role-per-membership — preserves `UserProfile.organization` for backwards compatibility, signals keep them in sync
- Primary org concept (`is_primary=True`) — single default to fall back to
- Organization switcher hidden for single-org users — no UI clutter for the common case

**Why (ROI tracking):** Sponsors asked "are AI insights actually useful?" Anecdotes weren't enough; needed quantitative measure of action-taken and outcome.

**Key decisions:**
- Action enum: Implemented, Investigating, Deferred, Partially Implemented, Dismissed — granularity to distinguish "ignored" from "evaluated and rejected"
- Outcome update is separate event — actions happen at decision time, outcomes weeks later
- Owner-or-admin delete — preserves audit trail; can't silently scrub failed actions

## v2.5 (2025-11-28) — P2P (Procure-to-Pay) Analytics module

**Why:** Customers consistently requested cycle-time analysis and 3-way matching exception management. Existing transaction-only analytics couldn't answer "why is this invoice late."

**Key decisions:**
- New models in `apps/procurement` (not new app) — P2P is procurement workflow, not separate domain
- `P2PAnalyticsService` does NOT inherit `BaseAnalyticsService` — chose pragmatic divergence over refactor blocker; tracked as Cross-Module Open
- `_avg_days_to_pay` consolidated to one staticmethod (8 call sites) — avoids the formula drift that bit prior analytics work
- 3-way matching uses `match_status='exception'` flag, not deletion — preserves audit trail

## v2.4 (2025-11-20) — Reports UI categorization + organization branding

**Why:** Customers needed white-labeled PDF reports and an easier way to find report types as the catalog grew past 10.

**Key decisions:**
- Report categorization (Executive, Supplier Intelligence, Trends, Optimization) — task-based grouping beat alphabetical when count grew
- Branding fields on `Organization` model with `get_branding()` accessor — single source of truth for logo, colors, footer
- PDF rendering via ReportLab (already a dependency) rather than headless browser — no Chromium ops burden in production

## v2.3 (2025-11-12) — Reports module launch

**Why:** Customers needed scheduled, exportable reports — interactive dashboards alone insufficient for executive sponsorship and audit committees.

**Key decisions:**
- 11 initial report types covering executive, spend, supplier, pareto, contract, savings dimensions
- Async generation via Celery for large reports — keep request/response under 30s
- Filter parameter shape mirrors transaction filter API — consistency between dashboard and report
- 4 report types added simultaneously (Stratification, Seasonality, YoY, Tail Spend) — these completed the Kraljic-matrix story already started in dashboards

## v2.2 (2025-11-04) — Backend-powered analytics + drill-down modals

**Why:** Client-side aggregation was hitting JS heap limits at >50K transactions. Drill-down was UX necessity for actionable analytics.

**Key decisions:**
- Pre-computed analytics on backend — sacrifices "any client filter, instant" for "any data size, fast"
- Per-page drill-down endpoints rather than generic — each chart's drill-down has unique data needs
- Organization context in query keys — superuser org-switching was breaking cache isolation

## v2.0 (2025-10-15) — Dashboard hardening + RBAC

**Why:** Customer security review required role-based access control before production deployment.

**Key decisions:**
- Three roles (admin, manager, viewer) — minimum viable hierarchy for procurement org chart
- HTTP-only cookies for JWT — XSS protection beat the developer-experience cost of localStorage
- Admin panel only for data uploads — prevents the "non-admin uploaded a 10K-row CSV that was wrong" failure mode
- Saved filter presets in localStorage — light-touch personalization without server-side state
