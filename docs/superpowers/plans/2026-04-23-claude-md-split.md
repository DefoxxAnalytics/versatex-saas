# CLAUDE.md Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trim root `CLAUDE.md` from 1,373 lines / 70.6k chars to ~380 lines / ~18k chars (-74%) by splitting into a three-layer context system: lean root + auto-discovered subdirectory breadcrumbs + on-demand canonical docs.

**Architecture:** Layer 1 root CLAUDE.md keeps every-session essentials (commands, ports, accuracy conventions, recent gotchas) and adds pointer blocks. Layer 2 breadcrumbs at `backend/apps/{procurement,analytics}/CLAUDE.md` auto-load when Claude touches those dirs. Layer 3 canonical docs at `docs/claude/{p2p,ai-insights}.md` provide deep module context. Drift-prone duplications (API endpoint enumerations, hook listings, test counts) are deleted entirely; rationale-only history moves to new `docs/CHANGELOG.md`.

**Tech Stack:** Markdown documentation only. Verification via `wc`, `grep`, and `git`. No code changes, no tests broken, no builds run.

**Spec reference:** [`docs/superpowers/specs/2026-04-23-claude-md-split-design.md`](../specs/2026-04-23-claude-md-split-design.md)

---

## File Structure

| Path | Action | Purpose |
|---|---|---|
| `docs/claude/p2p.md` | Create | Canonical P2P module reference |
| `docs/claude/ai-insights.md` | Create | Canonical AI Insights / LLM reference |
| `docs/CHANGELOG.md` | Create | Curated v2.0–v2.11 rationale |
| `backend/apps/procurement/CLAUDE.md` | Create | Auto-discovered breadcrumb → p2p.md |
| `backend/apps/analytics/CLAUDE.md` | Create | Auto-discovered breadcrumb → both docs/claude/ files |
| `CLAUDE.md` (root) | Modify | Major rewrite, ~74% size reduction |
| `docs/TECHNICAL_DEBT.md` | Modify | Append "Documentation audit candidates" section |
| `docs/development/CLAUDE.md` | Delete | Actively wrong (cites port 8001, pre-rebrand project name) |

**Three commits:**
- Commit 1 (Tasks 1–6): create 5 new files, then commit (additive, zero risk)
- Commit 2 (Tasks 7–9): rewrite root CLAUDE.md, then commit (substantive)
- Commit 3 (Tasks 10–12): delete stale dev CLAUDE.md, append audit-candidates note, then commit (cleanup)

---

## Task 1: Create `docs/claude/p2p.md`

**Files:**
- Create: `docs/claude/p2p.md`

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p "docs/claude"
```

Expected: no output, exit 0. Run `ls docs/claude/` and confirm directory exists (will be empty).

- [ ] **Step 2: Write the file with the complete content below**

Use the Write tool to create `docs/claude/p2p.md` with this exact content:

````markdown
# P2P (Procure-to-Pay) Module — Claude Reference

> **When to read this:** Editing files in `backend/apps/procurement/` that touch P2P models (PR/PO/GR/Invoice), or `backend/apps/analytics/p2p_*.py`, or any frontend hook in `useP2PAnalytics.ts`.
> **You can skip this if:** Working only on Transaction-level analytics, AI Insights, or unrelated frontend pages.

## Core invariants

1. **Document chain order is rigid: PR → PO → GR → Invoice → Payment.** No skipping stages. Models live in `backend/apps/procurement/models.py`.
2. **Match exceptions never delete invoices** — they set `Invoice.match_status='exception'` and surface in the matching API at `backend/apps/analytics/p2p_views.py`.
3. **`P2PAnalyticsService` does NOT inherit from `BaseAnalyticsService`.** This divergence is intentional, tracked in `docs/ACCURACY_AUDIT.md` Cross-Module Open. Filter validation is ad-hoc until that lands. **Do not refactor without coordination.**
4. **All P2P endpoints scope by `request.organization`** — never query unscoped or you leak across tenants.
5. **`P2PImportMixin` at `backend/apps/procurement/admin.py:1334`** is the source of truth for admin CSV column ordering. The drift-guard test at `backend/apps/authentication/tests/test_admin_export.py::TestColumnDriftGuard` will fail loudly if the export column constants drift from this importer — fix the cause, don't suppress the test.

## Primitives — use these, don't re-implement

| Primitive | Location | Purpose |
|---|---|---|
| `P2PAnalyticsService._avg_days_to_pay` | `backend/apps/analytics/p2p_services.py` (staticmethod) | Canonical "days from invoice to payment" calc — 8 call sites consolidated here |
| `P2PImportMixin` | `backend/apps/procurement/admin.py:1334` | Admin CSV import for PR/PO/GR/Invoice |
| `BaseAnalyticsService._get_fiscal_year` / `_get_fiscal_month` | `backend/apps/analytics/services/base.py:96-113` | FY math — but `P2PAnalyticsService` doesn't inherit, see divergence below |

## Known divergences (and why they exist)

- **`P2PAnalyticsService` doesn't inherit from `BaseAnalyticsService`.** Tracked as Cross-Module Open in `docs/ACCURACY_AUDIT.md`. Until consolidation lands, P2P services duplicate filter validation and FY math. Document divergence rather than refactor — see Accuracy Convention §8 in root CLAUDE.md.

## Cross-cutting gotchas

- **Amount-weighted rate companion fields (Convention §1).** Any new count-based rate (match rate, compliance rate, on-time rate) MUST also emit an `*_by_amount` companion. Example: `exception_rate_by_amount` at `backend/apps/analytics/p2p_services.py`.
- **3-Way Matching exception flow.** Mismatched invoices set `match_status='exception'`, do NOT delete. UI presents them via `/api/v1/analytics/matching/exceptions/`.
- **Bulk resolution endpoint exists.** `/api/v1/analytics/matching/exceptions/bulk-resolve/` — single notes modal applies to all selected violations. Frontend at `frontend/src/pages/Matching.tsx`.
- **Industry-aware seeding.** `seed_demo_data --industry healthcare` swaps in industry-specific departments, cost-center prefixes, payment terms, and policies. See `docs/DEMO_DATA.md`.

## API surface (orientation only)

P2P endpoints live under `/api/v1/analytics/p2p/`, `/api/v1/analytics/matching/`, `/api/v1/analytics/aging/`, `/api/v1/analytics/requisitions/`, `/api/v1/analytics/purchase-orders/`, `/api/v1/analytics/supplier-payments/`. Routing in `backend/apps/analytics/p2p_urls.py`.

Frontend hooks in `frontend/src/hooks/useP2PAnalytics.ts`.

To enumerate current endpoints: `grep -E "path\(" backend/apps/analytics/p2p_urls.py`.

## Test patterns

- P2P generator tests: `backend/apps/reports/tests/test_p2p_generators.py`
- Admin export drift-guard: `backend/apps/authentication/tests/test_admin_export.py`
- Run: `docker-compose exec backend pytest backend/apps/reports/tests/test_p2p_generators.py -v`
- Factory: `backend/apps/authentication/tests/factories.py::DemoOrganizationFactory(OrganizationFactory)` — has `is_demo=True`

## See also

- `backend/apps/procurement/models.py` — P2P model definitions
- `backend/apps/analytics/p2p_services.py` — `P2PAnalyticsService`
- `backend/apps/analytics/p2p_views.py` — DRF views
- `backend/apps/analytics/p2p_urls.py` — URL routing
- `frontend/src/hooks/useP2PAnalytics.ts` — frontend hooks
- `docs/ACCURACY_AUDIT.md` — Cross-Module Open ledger
- `docs/CHANGELOG.md` — v2.5 (P2P launch) and v2.11 (admin export) historical context
````

- [ ] **Step 3: Verify the file exists and is ~75 lines**

Run:
```bash
wc -l docs/claude/p2p.md
```

Expected: ~75 lines (acceptable range 70–85).

- [ ] **Step 4: Verify the "When to read" line is present (sanity check the structure)**

Run:
```bash
grep -c "^## " docs/claude/p2p.md
```

Expected: 7 (matches template: Core invariants, Primitives, Known divergences, Cross-cutting gotchas, API surface, Test patterns, See also).

---

## Task 2: Create `docs/claude/ai-insights.md`

**Files:**
- Create: `docs/claude/ai-insights.md`

- [ ] **Step 1: Write the file with the complete content below**

Use the Write tool to create `docs/claude/ai-insights.md` with this exact content:

````markdown
# AI Insights — Claude Reference

> **When to read this:** Editing files in `backend/apps/analytics/ai_*.py`, `rag_*.py`, or anything touching `LLMRequestLog` / `SemanticCache` / `EmbeddedDocument` models, or frontend hooks in `useAIInsights.ts`.
> **You can skip this if:** Working on non-AI analytics, P2P, or frontend pages that don't render AI insights or chat.

## Core invariants

1. **No silent fallback when AI enhancement is unavailable (Convention §6).** When `AIInsightsService` cannot enhance because no API key is configured, the response MUST omit the `ai_enhancement` key, and the frontend MUST render a "(Deterministic)" label. **Never silently substitute deterministic output for AI-enhanced output.**
2. **Tri-state enhancement status is a future feature, not current.** §6 covers only the no-key case. LLM-failure fallback is currently silent and tracked as Cross-Module Open in `docs/ACCURACY_AUDIT.md`.
3. **`AIInsightsService` calls Django ORM directly, NOT analytics services.** This divergence is documented per Convention §8 ("document don't refactor"). Do not "fix" by routing through analytics services unless coordinating a Cross-Module Open close.
4. **All AI endpoints scope by `request.organization`** — same tenant isolation invariant as P2P.
5. **Sensitive preference keys must be added to BOTH `MASKED_PREFERENCE_KEYS` AND masking sites.** Per Convention §5: masking happens in `UserProfileSerializer.to_representation` AND `UserPreferencesView.get` (which bypasses the serializer). Both sites required.

## Primitives — use these, don't re-implement

| Primitive | Location | Purpose |
|---|---|---|
| `AIInsightsService.deduplicate_savings` | `backend/apps/analytics/ai_services.py:873` (instance method) | Prevents double-counting savings across insight types |
| `UserProfile.mask_preferences` | `backend/apps/authentication/models.py` (staticmethod) | Masks sensitive preference keys per `MASKED_PREFERENCE_KEYS` |

## Known divergences (and why they exist)

- **`AIInsightsService` direct ORM access.** Bypasses analytics services. Documented per Convention §8 — refactor only if user-visible wrong number, not for DRY-ness alone.
- **Silent LLM-failure fallback.** When the LLM call fails (network, rate limit, etc.), enhancement falls back silently. Tracked as Cross-Module Open. Do not change without addressing the broader tri-state design.

## Cross-cutting gotchas

- **Two-site preference allowlist gate (Convention §5).** New `UserProfile.preferences` keys must be added to BOTH:
  - `ALLOWED_PREFERENCE_KEYS` at `backend/apps/authentication/models.py:167-170`
  - An explicit `Field()` declaration on `UserPreferencesSerializer` at `backend/apps/authentication/serializers.py`

  Otherwise the key is silently dropped at one of the two layers.
- **Sensitive keys need three sites:** `ALLOWED_PREFERENCE_KEYS`, `MASKED_PREFERENCE_KEYS`, AND masking call in `UserPreferencesView.get`.
- **Prompt caching strategy (90% cost reduction on cached reads).** Anthropic prompt caching applied to system prompts. Don't break the cache by injecting per-request data into cached blocks.
- **Semantic cache 0.90 similarity threshold.** Below 0.90, treat as miss. Tunable via `SemanticCache` model — but changes affect cost/quality tradeoff materially.
- **RAG embedding refresh runs Sundays 4 AM (Celery Beat).** Re-embeds supplier profiles + insights. Don't trigger ad-hoc except via the management endpoint `/api/v1/analytics/rag/refresh/`.
- **Streaming chat uses SSE** at `/api/v1/analytics/ai-insights/chat/stream/`. Frontend uses `useAIChatStream()` hook which manages message state across stream events.

## API surface (orientation only)

AI Insights endpoints live under `/api/v1/analytics/ai-insights/` (insights, feedback, chat, usage) and `/api/v1/analytics/rag/` (documents, search, ingest). Routing in `backend/apps/analytics/urls.py`.

Frontend hooks in `frontend/src/hooks/useAIInsights.ts`.

To enumerate current endpoints: `grep -E "path\(" backend/apps/analytics/urls.py | grep -E "ai-insights|rag"`.

## Models

| Model | Purpose | Location |
|---|---|---|
| `LLMRequestLog` | Tracks all LLM calls — tokens, cost, latency, cache hit | `backend/apps/analytics/models.py` |
| `SemanticCache` | pgvector embeddings for similarity search | `backend/apps/analytics/models.py` |
| `EmbeddedDocument` | RAG document store with vector embeddings | `backend/apps/analytics/models.py` |
| `InsightFeedback` | ROI tracking — actions and outcomes | `backend/apps/analytics/models.py` |

## Celery Beat schedule

| Task | Schedule | Purpose |
|---|---|---|
| `batch_generate_insights` | 2:00 AM daily | Generate insights for all orgs |
| `batch_enhance_insights` | 2:30 AM daily | AI-enhance for orgs with API keys |
| `cleanup_semantic_cache` | 3:00 AM daily | Remove expired/orphaned entries |
| `cleanup_llm_request_logs` | 3:30 AM daily | Archive logs older than 30 days |
| `refresh_rag_documents` | 4:00 AM Sundays | Re-embed supplier profiles + insights |

## Test patterns

- AI service tests: `backend/apps/analytics/tests/test_ai_services.py`
- Run: `docker-compose exec backend pytest backend/apps/analytics/tests/test_ai_services.py -v`
- Mock LLM calls — never hit the live API in tests

## See also

- `backend/apps/analytics/ai_services.py` — `AIInsightsService`
- `backend/apps/analytics/rag_services.py` — RAG / embedding service
- `backend/apps/analytics/models.py` — `LLMRequestLog`, `SemanticCache`, `EmbeddedDocument`, `InsightFeedback`
- `frontend/src/hooks/useAIInsights.ts` — frontend hooks
- `docs/ACCURACY_AUDIT.md` — Conventions §5 (preferences), §6 (no silent fallback), §8 (document don't refactor)
- `docs/CHANGELOG.md` — v2.6 (AI Insights ROI) and v2.9 (LLM enhancement) historical context
````

- [ ] **Step 2: Verify the file is ~110 lines**

Run:
```bash
wc -l docs/claude/ai-insights.md
```

Expected: ~110 lines (acceptable range 100–125).

- [ ] **Step 3: Verify section structure**

Run:
```bash
grep -c "^## " docs/claude/ai-insights.md
```

Expected: 9 (Core invariants, Primitives, Known divergences, Cross-cutting gotchas, API surface, Models, Celery Beat schedule, Test patterns, See also).

---

## Task 3: Create `docs/CHANGELOG.md`

**Files:**
- Create: `docs/CHANGELOG.md`

- [ ] **Step 1: Write the file with the complete content below**

Use the Write tool to create `docs/CHANGELOG.md` with this exact content:

````markdown
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
````

- [ ] **Step 2: Verify the file is ~130 lines**

Run:
```bash
wc -l docs/CHANGELOG.md
```

Expected: ~130 lines (acceptable range 120–140).

- [ ] **Step 3: Verify all 11 versions are present**

Run:
```bash
grep -c "^## v2\." docs/CHANGELOG.md
```

Expected: 11 (v2.0, v2.2, v2.3, v2.4, v2.5, v2.6, v2.7, v2.8, v2.9, v2.10, v2.11). Note: v2.1 was a patch release with no architectural decisions — intentionally omitted.

---

## Task 4: Create `backend/apps/procurement/CLAUDE.md` breadcrumb

**Files:**
- Create: `backend/apps/procurement/CLAUDE.md`

- [ ] **Step 1: Verify the target directory exists**

Run:
```bash
ls -d backend/apps/procurement/
```

Expected: directory listed, no error.

- [ ] **Step 2: Write the breadcrumb file**

Use the Write tool to create `backend/apps/procurement/CLAUDE.md` with this exact content:

```markdown
# Procurement App — Claude Context Pointer

You're working in the procurement app, which holds:
- Core data models: `Supplier`, `Category`, `Transaction`, `DataUpload`
- P2P models: `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `Invoice`

If your task touches any P2P model or workflow, read **[../../../docs/claude/p2p.md](../../../docs/claude/p2p.md)** first — it documents architectural invariants, the canonical primitives, and known divergences you must not "fix".

For accuracy conventions affecting all analytics, see root CLAUDE.md § "Analytics accuracy conventions" and `docs/ACCURACY_AUDIT.md`.
```

- [ ] **Step 3: Verify line count and target file path**

Run:
```bash
wc -l backend/apps/procurement/CLAUDE.md
```

Expected: 7 lines (acceptable range 6–10; spec hard cap is 15).

Run:
```bash
test -f docs/claude/p2p.md && echo "link target exists" || echo "BROKEN LINK"
```

Expected: `link target exists` (Task 1 created it).

---

## Task 5: Create `backend/apps/analytics/CLAUDE.md` breadcrumb

**Files:**
- Create: `backend/apps/analytics/CLAUDE.md`

- [ ] **Step 1: Verify the target directory exists**

Run:
```bash
ls -d backend/apps/analytics/
```

Expected: directory listed, no error.

- [ ] **Step 2: Write the breadcrumb file**

Use the Write tool to create `backend/apps/analytics/CLAUDE.md` with this exact content:

```markdown
# Analytics App — Claude Context Pointer

You're working in the analytics app, which contains:
- Core procurement analytics: `services.py`, `services/*.py`
- P2P analytics: `p2p_services.py`, `p2p_views.py`, `p2p_urls.py`
- AI Insights + LLM: `ai_services.py`, `rag_services.py`, embeddings, semantic cache, streaming chat

Module-specific gotchas (read when relevant):
- P2P work → **[../../../docs/claude/p2p.md](../../../docs/claude/p2p.md)**
- AI Insights / LLM / RAG / streaming → **[../../../docs/claude/ai-insights.md](../../../docs/claude/ai-insights.md)**

For accuracy conventions affecting all analytics, see root CLAUDE.md § "Analytics accuracy conventions" and `docs/ACCURACY_AUDIT.md`.
```

- [ ] **Step 3: Verify line count and link targets**

Run:
```bash
wc -l backend/apps/analytics/CLAUDE.md
```

Expected: 11 lines (acceptable range 10–14; spec hard cap is 15).

Run:
```bash
test -f docs/claude/p2p.md && test -f docs/claude/ai-insights.md && echo "both link targets exist" || echo "BROKEN LINK"
```

Expected: `both link targets exist`.

---

## Task 6: Verify Commit 1 changes and commit

- [ ] **Step 1: List all 5 new files**

Run:
```bash
ls -la docs/claude/p2p.md docs/claude/ai-insights.md docs/CHANGELOG.md backend/apps/procurement/CLAUDE.md backend/apps/analytics/CLAUDE.md
```

Expected: all 5 files listed with sizes >0.

- [ ] **Step 2: Verify total line counts are within target**

Run:
```bash
wc -l docs/claude/p2p.md docs/claude/ai-insights.md docs/CHANGELOG.md backend/apps/procurement/CLAUDE.md backend/apps/analytics/CLAUDE.md
```

Expected total: ~330 lines across all 5 files (rough sum of individual targets).

- [ ] **Step 3: Run git status to confirm only the new files are staged**

Run:
```bash
git status --short
```

Expected: 5 new files shown with `??` (untracked) prefix. No modifications to other files at this stage.

- [ ] **Step 4: Stage the 5 files explicitly (do not use `git add .`)**

Run:
```bash
git add docs/claude/p2p.md docs/claude/ai-insights.md docs/CHANGELOG.md backend/apps/procurement/CLAUDE.md backend/apps/analytics/CLAUDE.md
```

Expected: no output, exit 0.

- [ ] **Step 5: Commit**

Run:
```bash
git commit -m "$(cat <<'EOF'
docs(claude): add docs/claude/ canonical refs + app breadcrumbs + CHANGELOG

Three-layer context system per docs/superpowers/specs/2026-04-23-claude-md-split-design.md:

- docs/claude/p2p.md         — P2P module architectural invariants and primitives
- docs/claude/ai-insights.md — AI Insights conventions, LLM pipeline, RAG details
- docs/CHANGELOG.md          — Curated v2.0–v2.11 architectural decisions and rationale
- backend/apps/procurement/CLAUDE.md  — Auto-discovered breadcrumb to p2p.md
- backend/apps/analytics/CLAUDE.md    — Auto-discovered breadcrumb to both canonical docs

Additive change. Root CLAUDE.md unchanged in this commit; rewrite follows
in commit 2 of the split sequence.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: `[main <hash>] docs(claude): add docs/claude/...`, 5 files changed, ~330 insertions.

- [ ] **Step 6: Confirm clean state**

Run:
```bash
git status
```

Expected: "nothing to commit, working tree clean" (or notes about pre-existing untracked files unrelated to this work).

---

## Task 7: Rewrite root `CLAUDE.md` — preparation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Capture baseline metrics**

Run:
```bash
wc -l CLAUDE.md && wc -c CLAUDE.md
```

Expected: ~1373 lines, ~70600 chars (this is the "before" measurement to compare against later).

- [ ] **Step 2: Read the current file in full to confirm understanding before rewrite**

Read `CLAUDE.md` (no offset, default limit). Focus particularly on:
- Lines 1–187: Project Overview, Tech Stack, Dev Commands, API structure (most retained)
- Lines 188–246: Analytics accuracy conventions (preserved verbatim except prose tightening)
- Lines 247–296: Port Configuration, Env Vars, Security (kept compressed)
- Lines 297–442: Database Schema, Admin Users, Common Issues, CI/CD (mostly kept; CI/CD deleted)
- Lines 443–870: v2.11 + v2.10 + v2.9 detail (compress v2.11 to inline gotchas, v2.10 to compressed summary, move v2.9 detail to CHANGELOG)
- Lines 871–1373: v2.0–v2.8 historical changelog (rationale moved to CHANGELOG, prose deleted)

Confirm you can identify the boundaries of each section before proceeding.

---

## Task 8: Rewrite root `CLAUDE.md` — apply

- [ ] **Step 1: Write the new file using the Write tool**

Use the Write tool to overwrite `CLAUDE.md` with this exact content:

````markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Versatex Analytics — an enterprise-grade procurement analytics platform with organization-based multi-tenancy.

**Tech Stack:**
- Backend: Django 5.0 + Django REST Framework + PostgreSQL + Celery/Redis
- Frontend: React 18 + TypeScript + Tailwind CSS 4 + Vite
- Auth: JWT tokens with role-based access (admin, manager, viewer)

## Module-Specific Context

These canonical docs auto-load via subdirectory `CLAUDE.md` breadcrumbs at `backend/apps/procurement/` and `backend/apps/analytics/`. Read directly when working on these modules:

- **P2P Analytics** (cycle, matching, aging, requisitions, POs, payments) → [docs/claude/p2p.md](docs/claude/p2p.md)
- **AI Insights / LLM / RAG / Streaming Chat** → [docs/claude/ai-insights.md](docs/claude/ai-insights.md)

## External References

- **Accuracy conventions ledger** (full background, Cross-Module Open tracker) → [docs/ACCURACY_AUDIT.md](docs/ACCURACY_AUDIT.md)
- **Demo data seeding** (industry profiles, command reference) → [docs/DEMO_DATA.md](docs/DEMO_DATA.md)
- **Architectural decision history** (the "why" behind v2.0–v2.11) → [docs/CHANGELOG.md](docs/CHANGELOG.md)
- **Production deployment** (Railway) → [docs/RAILWAY-DEPLOY-WALKTHROUGH.md](docs/RAILWAY-DEPLOY-WALKTHROUGH.md)
- **First-time setup** → [docs/setup/QUICK_START_GUIDE.md](docs/setup/QUICK_START_GUIDE.md)
- **Docker troubleshooting** → [docs/setup/DOCKER-TROUBLESHOOTING.md](docs/setup/DOCKER-TROUBLESHOOTING.md)
- **Windows-specific setup** → [docs/setup/WINDOWS-SETUP.md](docs/setup/WINDOWS-SETUP.md)
- **Adding users to organizations** → [docs/onboarding/ASSIGN_USER_TO_ORGANIZATION.md](docs/onboarding/ASSIGN_USER_TO_ORGANIZATION.md)
- **Tenant provisioning** → [docs/onboarding/TENANT_PROVISIONING.md](docs/onboarding/TENANT_PROVISIONING.md)

## Development Commands

### Docker Development (Recommended)

```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Collect static files (after changing backend/static/)
docker-compose exec backend python manage.py collectstatic --noinput

# Force rebuild frontend (when changes aren't reflected)
docker-compose up -d --build --force-recreate frontend
```

### Local Development

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py runserver

# Frontend
cd frontend
pnpm install
pnpm dev
```

### Testing

```bash
# Backend tests
docker-compose exec backend pytest                          # all tests
docker-compose exec backend pytest apps/authentication      # specific app
docker-compose exec backend pytest --cov=apps               # with coverage

# Frontend tests
cd frontend
pnpm test           # watch mode
pnpm test:run       # single run
pnpm test:run --coverage
```

### Demo Data Seeding

```bash
# Healthcare
docker-compose exec backend python manage.py seed_industry_data --industry healthcare --org-slug uch --wipe
docker-compose exec backend python manage.py seed_demo_data --org uch --industry healthcare --wipe

# Higher Education
docker-compose exec backend python manage.py seed_industry_data --industry higher-ed --org-slug tsu --wipe
docker-compose exec backend python manage.py seed_demo_data --org tsu --industry higher-ed --wipe

# Manufacturing (org slug `eaton` = Bolt & Nuts Manufacturing)
docker-compose exec backend python manage.py seed_demo_data --org eaton --wipe
```

Both commands are idempotent via `--wipe` and deterministic via `--seed` (default 42). Full reference: [docs/DEMO_DATA.md](docs/DEMO_DATA.md). Industry profile data lives in [backend/apps/procurement/management/commands/_industry_profiles.py](backend/apps/procurement/management/commands/_industry_profiles.py).

### Type Checking & Linting

```bash
# Frontend
cd frontend
pnpm check          # TypeScript check (tsc --noEmit)
pnpm format         # Prettier format
pnpm format --check # Check formatting without changes

# Backend (install dev deps: pip install black isort flake8)
cd backend
black --check .     # Check Python formatting
black .             # Apply formatting
isort --check .     # Check import sorting
flake8 .            # Lint Python code
```

## Architecture

### Backend Structure (`backend/`)

```
backend/
├── apps/
│   ├── authentication/     # User, Organization, UserProfile, UserOrganizationMembership, AuditLog
│   ├── procurement/        # Supplier, Category, Transaction, DataUpload + P2P models (PR, PO, GR, Invoice)
│   ├── analytics/          # AnalyticsService + P2PAnalyticsService + AIInsightsService
│   └── reports/            # Report generation, scheduling, export (PDF/Excel/CSV)
├── config/                 # Django settings, URLs, Celery config
└── templates/admin/        # Custom Django admin templates (navy theme)
```

**Key patterns:**
- All data models scoped by `organization` ForeignKey for multi-tenancy
- JWT auth via `djangorestframework-simplejwt` with token refresh
- Celery worker for background tasks (CSV processing, reports, AI batch jobs)
- See `docs/claude/p2p.md` for P2P module deep-dive, `docs/claude/ai-insights.md` for AI Insights

### Frontend Structure (`frontend/src/`)

```
src/
├── components/             # shadcn/ui components, DashboardLayout, ProtectedRoute
├── contexts/               # AuthContext, OrganizationContext, ThemeContext
├── hooks/                  # Domain-specific data-fetching hooks
├── lib/                    # api.ts (Axios client), auth.ts, analytics.ts
└── pages/                  # Route components (lazy-loaded)
```

**Key patterns:**
- Wouter for routing (not React Router)
- TanStack Query v5 for server state
- All pages lazy-loaded for code splitting
- Axios interceptors handle JWT refresh
- Admin panel link gated on `user.profile.role === 'admin'`

### API Structure

```
/api/v1/auth/          # login, register, logout, token/refresh, user, change-password
/api/v1/procurement/   # suppliers, categories, transactions (CRUD, upload_csv, bulk_delete, export)
/api/v1/analytics/     # overview, spend-by-*, pareto, tail-spend, monthly-trend, stratification, etc.
/api/v1/analytics/ai-insights/  # AI insights, feedback, ROI, deep analysis (see docs/claude/ai-insights.md)
/api/v1/analytics/p2p/ # P2P analytics: cycle, matching, aging, requisitions, POs, payments (see docs/claude/p2p.md)
/api/v1/reports/       # Report generation, scheduling, downloads
```

Legacy endpoints (`/api/auth/`, `/api/procurement/`, `/api/analytics/`) supported for backwards compatibility.

To enumerate current endpoints: `grep -r "path(" backend/apps/*/urls.py`. Frontend client interfaces in `frontend/src/lib/api.ts`.

## Analytics Accuracy Conventions

Conventions established by the 8-cluster accuracy audit (closed 2026-04-22). Full background: [docs/ACCURACY_AUDIT.md](docs/ACCURACY_AUDIT.md). Apply to any new work in `apps/analytics/`, `apps/reports/generators/`, and `apps/authentication/` preferences plumbing.

### 1. Amount-weighted rate companion fields

Count-based rates (match, compliance, on-time) MUST emit an `*_by_amount` companion when exposed in the UI. A 95% count-based match rate on low-value invoices can coexist with a 60% amount-weighted rate.

**Shipped examples:** `exception_rate_by_amount` (3-Way Matching), amount-weighted compliance rate (Maverick/Compliance), `on_time_eligible_count` denominator (PO leakage).

### 2. Deprecated alias lifetime when renaming response fields

When renaming a response field, keep the old key as a deprecated alias for one release. Mark both in TypeScript with `@deprecated` JSDoc.

**Example:** AP aging emits both `days_to_pay` (canonical) and `avg_days_to_pay` (deprecated alias); `AgingOverview` interface in `frontend/src/lib/api.ts` reflects both. Add a concrete trigger criterion (version or date) before removing — "deprecated for one release" is ambiguous without a release cadence.

### 3. Fiscal-year math goes through the base helpers

All FY calculations route through `BaseAnalyticsService._get_fiscal_year()` / `_get_fiscal_month(date, use_fiscal_year=True)` at `backend/apps/analytics/services/base.py:96-113`. No inline re-implementations. Per-org FY-start override is a pending Cross-Module Open — when it lands, in exactly one place.

### 4. Growth metrics require equal-span windows

Any YoY, 6-month, or 3-month growth metric must omit its key (or emit `insufficient_data_for_*: true`) when fewer than two full windows of data exist. Never fall back to partial windows — root cause of the Predictive 13-month ~1100% anomaly.

### 5. `ALLOWED_PREFERENCE_KEYS` two-site gate

New keys on `UserProfile.preferences` must be added to **both**:
- `ALLOWED_PREFERENCE_KEYS` at `backend/apps/authentication/models.py:167-170` (otherwise silently dropped by the model)
- An explicit `Field()` on `UserPreferencesSerializer` at `backend/apps/authentication/serializers.py` (otherwise silently dropped by the serializer)

Sensitive keys (API keys, tokens, secrets) also require `MASKED_PREFERENCE_KEYS` entry AND masking in both `UserProfileSerializer.to_representation` AND `UserPreferencesView.get` (which bypasses the serializer).

### 6. No-silent-fallback when AI enhancement is unavailable

When `AIInsightsService` cannot enhance because no API key is configured, the response **must** omit the `ai_enhancement` key, and the frontend **must** render a "(Deterministic)" label. No silent fallback — users cannot tell otherwise.

Scope: this rule covers only the no-key case. Tri-state `enhancement_status` covering LLM-failure separately is tracked as Cross-Module Open; until it lands, LLM-failure fallback remains silent.

### 7. Class-C relabels change labels, not response shape

When a metric is mislabeled (e.g., "DPO" that is actually "Avg Days to Pay"), the fix is a UI-label change plus optional field rename with deprecated alias (§2). Do NOT add brand-new response fields — those are feature additions, not accuracy fixes.

### 8. Document-don't-refactor for divergent shared primitives

When a shared primitive (DPO, HHI, amount-weighted rate) is re-implemented in another service rather than imported, **document the divergence in the ledger**. Refactor only when the divergence produces a user-visible wrong number. The `ai_services.py` direct-ORM divergence vs analytics services is the canonical example — currently documented, not refactored.

### 9. Reusable primitives — prefer these over re-implementation

| Primitive | Location | Purpose |
|---|---|---|
| `BaseAnalyticsService._get_fiscal_year` / `_get_fiscal_month` | `backend/apps/analytics/services/base.py` | FY math (Jul–Jun default) |
| `BaseAnalyticsService._validate_filters` | `backend/apps/analytics/services/base.py` | Date-range + amount-range filter validation |
| `P2PAnalyticsService._avg_days_to_pay` | `backend/apps/analytics/p2p_services.py` (staticmethod) | Canonical "days from invoice to payment" calc — 8 call sites consolidated |
| `apps.analytics.services.yoy._yoy_change` | `backend/apps/analytics/services/yoy.py` | YoY delta with is_new/is_discontinued/insufficient_data flags |
| `AIInsightsService.deduplicate_savings` | `backend/apps/analytics/ai_services.py:873` (instance method) | Prevents double-counting across insight types |
| `UserProfile.mask_preferences` | `backend/apps/authentication/models.py` (staticmethod) | Masks sensitive preference keys per `MASKED_PREFERENCE_KEYS` |

Note: `P2PAnalyticsService` does NOT inherit from `BaseAnalyticsService` — divergence tracked as Cross-Module Open. Until that lands, P2P filter validation is ad-hoc.

## Port Configuration

Non-default host ports avoid collisions with other projects on 3000/5432/6379/8001/5555. All host ports parameterized in `docker-compose.yml` via env vars (defaults below).

- Frontend: `http://localhost:3001` (`FRONTEND_PORT`)
- Backend API: `http://localhost:8002/api` (`BACKEND_PORT`, container port 8000)
- Django Admin: `http://localhost:8002/admin`
- API Docs: `http://localhost:8002/api/docs`
- PostgreSQL: `localhost:5433` (`DB_PORT`)
- Redis: `localhost:6380` (`REDIS_PORT`)
- Flower: `http://localhost:5556` (`FLOWER_PORT`)

Container names prefixed `vstx-saas-*` (e.g., `vstx-saas-backend`). `docker-compose exec <service> ...` uses service names (`backend`, `db`, `redis`), unchanged.

## Environment Variables

Copy `.env.example` to `.env` and configure. Required minimums:

```env
SECRET_KEY=...           # python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=True               # False in production
DB_PASSWORD=...
VITE_API_URL=http://127.0.0.1:8002/api
```

See `.env.example` for the full list and the production security checklist.

## Security Features

**Rate limiting:** Uploads 10/hr/user, exports 30/hr/user, bulk deletes 10/hr/user, login 5/min, anonymous 100/hr, authenticated 1000/hr.

**Production deployment:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
Production override: no external DB/Redis ports, Redis auth, `DEBUG=False`, HTTPS-only CORS, container resource limits, read-only frontend FS, `no-new-privileges:true`.

**Security headers** (in `frontend/nginx/nginx.conf`): `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (geo/mic/cam/payment/usb disabled), CSP.

**Production checklist:** Generate new `SECRET_KEY`, set `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, deploy with prod compose, verify headers via `curl -I`.

## Database Schema Notes

- `Organization` — multi-tenant root, all data scoped to org. Has `is_demo: BooleanField` flag (v2.11) for synthetic-data tenants.
- `UserProfile` — extends Django User with org, role (admin/manager/viewer)
- `UserOrganizationMembership` — many-to-many between User and Organization with per-org role (multi-org users)
- `Transaction` — core data model with supplier/category FKs, amount, date
- `DataUpload` — tracks CSV upload history with `batch_id`

**P2P models** (in `apps/procurement/models.py`):
- `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `Invoice`
- See [docs/claude/p2p.md](docs/claude/p2p.md) for the model relationships, invariants, and matching workflow.

## Creating Admin Users

See [docs/onboarding/ASSIGN_USER_TO_ORGANIZATION.md](docs/onboarding/ASSIGN_USER_TO_ORGANIZATION.md) for the full procedure (Django shell snippets, admin UI, and API approaches).

## Common Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Login 403/500 errors | User lacks `UserProfile` with active organization | Create profile via `docs/onboarding/ASSIGN_USER_TO_ORGANIZATION.md` |
| Frontend changes not reflecting | Vite build cache | `docker-compose up -d --build --force-recreate frontend` |
| Static files missing in admin | Static not collected | `docker-compose exec backend python manage.py collectstatic --noinput` |
| Port 8002 in use | Conflict with other project | Override `BACKEND_PORT` in `.env` |

## Deployment

Production target: **Railway** (2-subdomain architecture: `app.*` frontend, `api.*` backend). Deploy preparation merged in PR #1 at commit `b952570`.

- **Step-by-step Railway walkthrough:** [docs/RAILWAY-DEPLOY-WALKTHROUGH.md](docs/RAILWAY-DEPLOY-WALKTHROUGH.md)
- **Hetzner VPS alternative:** [docs/FIRST-DEPLOY-WALKTHROUGH.md](docs/FIRST-DEPLOY-WALKTHROUGH.md)
- **Detailed runbooks:** `docs/deployment/` (DEPLOY-PLAYBOOK, MONITORING, CLOUDFLARE-EDGE)

## CI/CD

GitHub Actions runs on push/PR to `main`: backend lint (black, isort, flake8), Django tests (with PostgreSQL + Redis services), frontend TypeScript check, Prettier, Vitest, production builds, Docker image builds, Trivy security scan.

[![CI](https://github.com/DefoxxAnalytics/versatex-saas/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/DefoxxAnalytics/versatex-saas/actions/workflows/ci.yml)

## Recent Updates (v2.11) — Demo Tenant Support

Added `Organization.is_demo` BooleanField to distinguish synthetic-data tenants from real customers, plus an admin export action.

**Load-bearing gotchas:**
- **Three serializer paths for `is_demo`:** `OrganizationSerializer.is_demo`, `UserOrganizationMembershipSerializer.organization_is_demo`, `UserProfileSerializer.organization_is_demo`. Updating the field requires touching all three — `OrganizationSwitcher` synthesizes orgs from memberships on one branch and hits `/auth/organizations/` on the other.
- **Admin "Export seeded dataset as ZIP"** action is superuser-gated AND demo-org-only. Rejects entire queryset if any selected org has `is_demo=False` (no silent partial export).
- **Drift-guard test** at `backend/apps/authentication/tests/test_admin_export.py::TestColumnDriftGuard` will fail if exporter column constants drift from importer source-of-truth (`p2p_import_fields`, `CSVProcessor.REQUIRED_COLUMNS`). Fix the cause, don't suppress.
- New `AuditLog.ALLOWED_DETAIL_KEYS` entries: `is_demo`, `row_counts`, `zip_bytes`.

Full implementation history: [docs/CHANGELOG.md § v2.11](docs/CHANGELOG.md).

## Previous Updates (v2.10) — Brand Color Scheme + Demo Data Seeding

Third `colorScheme` option `"versatex"` added (alongside `"navy"` / `"classic"`) using grayscale chrome with brand yellow `#FDC00F` accent. Two new management commands stand up realistic, industry-specific demo environments.

**Load-bearing gotchas:**
- **Three-whitelist gate for adding any new color scheme:** TypeScript `ColorScheme` union (`useSettings.ts`, `api.ts`), backend `ChoiceField` (`serializers.py`), AND runtime `saveSettingsToStorage()` allowlist. Missing any one silently coerces back to `"navy"`.
- **Spend Distribution donut keeps red/yellow/green** — those are semantic risk tiers (High/Medium/Low value), not decoration. Don't replace with brand palette.
- **Demo orgs:** `eaton` (Bolt & Nuts Manufacturing), `uch` (Mercy Regional Medical Center), `tsu` (Pacific State University). Slugs preserved across renames.

Full implementation history: [docs/CHANGELOG.md § v2.10](docs/CHANGELOG.md).
````

- [ ] **Step 2: Verify the new file size meets target**

Run:
```bash
wc -l CLAUDE.md && wc -c CLAUDE.md
```

Expected: ~360–400 lines, ~17000–19500 chars. The hard cap is <20,000 chars (50% under threshold).

If chars are over 20000, identify the longest section and tighten further.

---

## Task 9: Verify Commit 2 changes and commit

- [ ] **Step 1: Cross-reference integrity check**

Run:
```bash
grep -oE '\[.*?\]\(([^)]+\.md[^)]*)\)' CLAUDE.md | grep -oE '\(([^)]+)\)' | tr -d '()' | sort -u
```

Expected: list of all linked .md files. Each should resolve. Then verify each:
```bash
for f in $(grep -oE '\[.*?\]\(([^)]+\.md[^)]*)\)' CLAUDE.md | grep -oE '\(([^)]+)\)' | tr -d '()' | sort -u); do test -f "$f" && echo "OK: $f" || echo "MISSING: $f"; done
```

Expected: every line prefixed `OK:`. Any `MISSING:` line is a broken link to fix before commit.

- [ ] **Step 2: Section structure sanity check**

Run:
```bash
grep -c "^## " CLAUDE.md
```

Expected: 12–16 top-level sections.

Run:
```bash
grep -c "^### " CLAUDE.md
```

Expected: 18–28 subsections.

- [ ] **Step 3: Content preservation — all 9 accuracy conventions present**

Run:
```bash
grep -E "^### [1-9]\." CLAUDE.md
```

Expected: 9 lines, headings `### 1.` through `### 9.` (the accuracy convention numbering).

- [ ] **Step 4: Content preservation — primitives table present with 6 rows**

Run:
```bash
grep -A 10 "Reusable primitives" CLAUDE.md | grep -c "^|"
```

Expected: 8 (1 header + 1 separator + 6 data rows).

- [ ] **Step 5: Content preservation — load-bearing strings present**

Run:
```bash
for s in "BACKEND_PORT" "ALLOWED_PREFERENCE_KEYS" "is_demo" "P2PAnalyticsService" "deduplicate_savings" "no-silent-fallback" "Versatex Analytics"; do
  grep -q "$s" CLAUDE.md && echo "OK: $s" || echo "MISSING: $s"
done
```

Expected: all `OK:`. Any `MISSING:` is a content drop bug.

- [ ] **Step 6: Stage and commit**

Run:
```bash
git add CLAUDE.md
git status --short
```

Expected: `M  CLAUDE.md` and nothing else.

Run:
```bash
git commit -m "$(cat <<'EOF'
docs(claude): trim root CLAUDE.md from 70k→18k chars (-74%)

Substantive rewrite per docs/superpowers/specs/2026-04-23-claude-md-split-design.md.

Retained verbatim or with light compression:
- Project Overview, Tech Stack, Development Commands, Type Checking
- Analytics Accuracy Conventions §1–9 + primitives table (rules verbatim;
  prose tightened ~30%)
- Port Configuration, Environment Variables (compressed), Security Features
  (compressed to bullets), Database Schema Notes, Common Issues, CI/CD

Added (new pointer sections):
- Module-Specific Context → docs/claude/p2p.md, docs/claude/ai-insights.md
- External References → ACCURACY_AUDIT, DEMO_DATA, CHANGELOG, deploy walkthroughs,
  setup guides, onboarding docs
- Deployment subsection → Railway walkthrough + Hetzner alt

Compressed v2.10/v2.11 to inline gotchas only (three-serializer-paths trap,
three-whitelist trap); narrative moved to docs/CHANGELOG.md.

Deleted (drift-prone or rediscoverable from source):
- Full P2P API endpoint enumerations (~85 lines) — discoverable in p2p_urls.py
- Full AI Insights API enumerations, both copies (~130 lines) — duplicate +
  discoverable in urls.py
- Test counts and file inventories (~80 lines) — rots every CI run
- Frontend hook name listings (~70 lines) — discoverable in hooks/
- v2.0–v2.9 narrative changelog (~560 lines) — rationale moved to CHANGELOG

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: `[main <hash>] docs(claude): trim root CLAUDE.md...`, 1 file changed.

- [ ] **Step 7: Final size confirmation**

Run:
```bash
wc -l CLAUDE.md && wc -c CLAUDE.md
```

Expected: <20,000 chars. Document the actual numbers to compare against the 70.6k baseline.

---

## Task 10: Delete `docs/development/CLAUDE.md`

**Files:**
- Delete: `docs/development/CLAUDE.md`

- [ ] **Step 1: Confirm file exists before deleting**

Run:
```bash
ls -la docs/development/CLAUDE.md
```

Expected: file listed. If missing, skip to Task 11.

- [ ] **Step 2: Delete via git rm**

Run:
```bash
git rm docs/development/CLAUDE.md
```

Expected: `rm 'docs/development/CLAUDE.md'`.

- [ ] **Step 3: Confirm `docs/development/` directory is now empty (or delete it too if empty)**

Run:
```bash
ls -la docs/development/
```

Expected: only `.` and `..` shown if empty. If empty, optionally remove the directory:
```bash
rmdir docs/development/
```
(If `rmdir` fails because of hidden files, leave the directory.)

---

## Task 11: Append "Documentation audit candidates" to `docs/TECHNICAL_DEBT.md`

**Files:**
- Modify: `docs/TECHNICAL_DEBT.md` (append at end)

- [ ] **Step 1: Read the current end of the file to understand existing structure**

Run:
```bash
tail -20 docs/TECHNICAL_DEBT.md
```

Note: confirm the file ends cleanly (no trailing partial section) and observe the heading style used (likely `##` for top-level sections).

- [ ] **Step 2: Append the new section**

Use the Edit tool with `replace_all: false`. The `old_string` should be the last paragraph of the file (read from Step 1 output to get exact text). The `new_string` should be that same last paragraph followed by a blank line and the new section below.

Section to append (with one preceding blank line):

```markdown

## Documentation audit candidates (added 2026-04-23)

These docs may be partially stale; verify before relying on them as authoritative references for Claude Code sessions or customer-facing documentation:

- `docs/AI_INSIGHTS - v1.0.md` — version suffix suggests pre-v2.9 enhancement work
- `docs/AI_INSIGHTS_ENHANCEMENT_PLAN.md` — planning doc for v2.9, not current reference
- `docs/P2P_ANALYTICS_SUITE.md` — implementation plan from v2.5 launch, not maintained as reference
- `docs/P2P_USER_GUIDE.md` — user-facing guide; verify UI screenshots and workflows still match
- `docs/SECURITY_AUDIT_REPORT.md` — audit snapshot from 2026-01-08, post-v2.7 hardening; currency unverified
- `docs/REPOSITORY_PATTERN_IMPLEMENTATION_PLAN.md` — implementation plan; verify whether pattern was adopted

Flagged during the 2026-04-23 root CLAUDE.md split (see `docs/superpowers/specs/2026-04-23-claude-md-split-design.md`). Audit individually and either refresh, archive to `docs/archive/`, or link from root CLAUDE.md once verified current.
```

- [ ] **Step 3: Verify the section was added cleanly**

Run:
```bash
tail -20 docs/TECHNICAL_DEBT.md
```

Expected: the appended section visible at the end. Run:
```bash
grep -c "Documentation audit candidates" docs/TECHNICAL_DEBT.md
```
Expected: 1.

---

## Task 12: Verify Commit 3 changes and commit

- [ ] **Step 1: Confirm both changes are staged**

Run:
```bash
git status --short
```

Expected:
```
D  docs/development/CLAUDE.md
M  docs/TECHNICAL_DEBT.md
```

If `docs/TECHNICAL_DEBT.md` shows `??` or doesn't appear, stage it:
```bash
git add docs/TECHNICAL_DEBT.md
```

- [ ] **Step 2: Commit**

Run:
```bash
git commit -m "$(cat <<'EOF'
docs(claude): delete stale docs/development/CLAUDE.md + flag audit candidates

Cleanup commit per docs/superpowers/specs/2026-04-23-claude-md-split-design.md.

Deleted: docs/development/CLAUDE.md
- Cited port 8001 (current reality: 8002)
- Used pre-rebrand project name analytics-dashboard-fullstack-7
- Missing all v2.5–v2.11 features
- Net-negative — actively misleading. Git history preserves it.

Modified: docs/TECHNICAL_DEBT.md
- Appended "Documentation audit candidates" listing 6 docs/ files whose
  currency is unverified after the v2.11 reset. Out-of-scope for this
  effort per spec Q2 decision (A); flagged here for follow-up audit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: `[main <hash>] docs(claude): delete stale...`, 2 files changed.

- [ ] **Step 3: Final tree-clean verification**

Run:
```bash
git status
```

Expected: "nothing to commit, working tree clean" except for any pre-existing untracked files unrelated to this work (e.g., screenshots from earlier session).

- [ ] **Step 4: Summary report**

Run:
```bash
git log --oneline -3
wc -c CLAUDE.md
```

Expected:
- 3 most recent commits are the three "docs(claude): ..." commits in order
- `CLAUDE.md` is <20,000 chars

Report back with:
- Original char count: 70,600
- New char count: [actual]
- Reduction: [actual %]
- Three commit hashes

---

## Task 13: Functional smoke test (next session, optional)

This task cannot run in the same session as the migration — it requires a fresh Claude Code session to test auto-discovery of breadcrumb files. Skip if not testing.

- [ ] **Step 1: Open a backend analytics file in a fresh Claude Code session**

In a new session, use the Read tool on `backend/apps/analytics/p2p_services.py`.

- [ ] **Step 2: Verify session-start banner mentions the breadcrumb**

Look in the session-start system reminder for a reference to `backend/apps/analytics/CLAUDE.md`. Claude Code's parent-directory auto-discovery should have loaded it.

If the breadcrumb is NOT auto-loaded, the discovery model has failed. Fall back: add the same content as explicit pointers in root CLAUDE.md and remove the breadcrumb files.

- [ ] **Step 3: Test relevance triggering**

Ask Claude (in that session): "What's the canonical primitive for days-to-pay in this codebase?"

Expected: Claude reads `docs/claude/p2p.md` (mentioned by breadcrumb), finds `P2PAnalyticsService._avg_days_to_pay`, and reports it without needing to grep.

If Claude greps blindly without consulting the canonical doc, the discovery is partially broken — the breadcrumb is loaded but Claude isn't following the pointer. Consider strengthening the breadcrumb language to be more imperative.

---

## Acceptance Criteria

| Criterion | Pass condition | Verified by |
|---|---|---|
| Size reduction | Root CLAUDE.md < 20,000 chars | Task 9 Step 7 |
| Threshold compliance | No "Large CLAUDE.md" performance warning | Task 9 Step 7 |
| Link integrity | All `docs/` links in root resolve | Task 9 Step 1 |
| Accuracy conventions intact | All 9 rules + primitives table present | Task 9 Steps 3, 4 |
| Module gotchas accessible | `docs/claude/p2p.md` and `docs/claude/ai-insights.md` exist with template structure | Task 1 Step 4, Task 2 Step 3 |
| Auto-discovery works | Editing `apps/analytics/*.py` triggers breadcrumb load | Task 13 Step 2 |
| No content lost silently | Critical invariants greppable in root | Task 9 Step 5 |
| Stale dev CLAUDE.md removed | `docs/development/CLAUDE.md` does not exist | Task 10 Step 2 |
| Audit candidates flagged | `docs/TECHNICAL_DEBT.md` ends with new section | Task 11 Step 3 |
| Three commits in order | `git log --oneline -3` shows the three split commits | Task 12 Step 4 |
