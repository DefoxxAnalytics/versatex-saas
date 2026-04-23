# CLAUDE.md Split — Design Spec

**Date:** 2026-04-23
**Author:** Brainstorming session (user + Claude)
**Status:** Approved, ready for implementation planning

## Problem

Root `CLAUDE.md` is 1,373 lines / 70,600 chars — 77% over the 40,000-char performance threshold ("Large CLAUDE.md will impact performance"). Every Claude Code session loads the full file, costing ~18k tokens and degrading instruction-following attention.

Root cause is not formatting bloat but **scope creep**: the file accumulated ~560 lines of "Previous Updates v2.0–v2.9" historical changelog, full API endpoint enumerations duplicated from `urls.py`, hook name listings duplicated from source, test file inventories with rot-prone counts, and module-specific architectural notes that span only one functional area.

The crown jewel — the 9-rule "Analytics accuracy conventions" section established by the 2026-04-22 audit — risks being diluted by the surrounding bloat.

## Goals

1. Reduce always-loaded context by ≥70% without losing any load-bearing invariant.
2. Move drift-prone content to source-of-truth (`urls.py`, `hooks/`, `pytest`) and delete the duplicates.
3. Move module-specific deep context to dedicated files that load *only* when the module is being touched.
4. Preserve discovery — Claude must not "miss" the moved content when it's actually needed.
5. Eliminate the actively-misleading `docs/development/CLAUDE.md` (cites wrong ports, pre-rebrand project name).

## Non-Goals

- Auditing/refreshing the 6 uncertain docs in `docs/` (`AI_INSIGHTS - v1.0.md`, `AI_INSIGHTS_ENHANCEMENT_PLAN.md`, `P2P_ANALYTICS_SUITE.md`, `P2P_USER_GUIDE.md`, `SECURITY_AUDIT_REPORT.md`, `REPOSITORY_PATTERN_IMPLEMENTATION_PLAN.md`). Flagged as future work in `TECHNICAL_DEBT.md`.
- Trimming the global `~/.claude/CLAUDE.md` (different scope, user's call).
- Restructuring `docs/onboarding/`, `docs/setup/`, `docs/deployment/` (already organized fine).
- Touching `docs/ACCURACY_AUDIT.md` or `docs/DEMO_DATA.md` (current and Claude-friendly).
- Reorganizing the project's source code (this is a documentation refactor only).

## Architecture

Three-layer context system:

```
Layer 1 — Root CLAUDE.md (always loaded, ~18k chars)
├── Every-session essentials: commands, ports, env, accuracy
│   conventions, security, schema, common issues, v2.10/v2.11 notes
├── Module-Specific Context pointer block → (Layer 3)
└── External References pointer block → docs/ existing files

Layer 2 — Subdirectory CLAUDE.md breadcrumbs (auto-loaded on touch)
├── backend/apps/procurement/CLAUDE.md  — ~8-line pointer
└── backend/apps/analytics/CLAUDE.md    — ~12-line pointer

Layer 3 — Canonical Claude-tailored docs (read on demand)
├── docs/claude/p2p.md         — P2P architectural gotchas + primitives
└── docs/claude/ai-insights.md — AI Insights conventions + LLM pipeline

Layer 4 — Reference docs (already exist, linked from Layer 1)
├── docs/ACCURACY_AUDIT.md
├── docs/DEMO_DATA.md
├── docs/CHANGELOG.md (NEW)
├── docs/RAILWAY-DEPLOY-WALKTHROUGH.md
└── docs/setup/, docs/onboarding/, docs/deployment/
```

**Information flow:** Claude starts session → reads global + root CLAUDE.md (~18k chars) → opens a file in `apps/analytics/` → auto-loads breadcrumb (~300 chars) → breadcrumb directs to `docs/claude/ai-insights.md` → reads only if relevant to task.

**Session cost by task type:**

| Session type | Always-loaded | On-demand reads |
|---|---|---|
| Frontend-only work | ~18k chars (root only) | — |
| Backend analytics work | ~18.3k (root + breadcrumb) | +p2p.md or ai-insights.md if relevant |
| Deployment work | ~18k (root) | +RAILWAY-DEPLOY-WALKTHROUGH.md |
| Cross-cutting refactor | ~18.6k (root + both breadcrumbs) | +both docs/claude/*.md |

## Components

### Layer 1 — Root `CLAUDE.md` (rewritten)

**Sections retained (verbatim or with light compression):**
- Project Overview + Tech Stack — verbatim
- Development Commands (Docker, local, testing, demo data seeding) — verbatim
- Type Checking & Linting — verbatim
- Analytics Accuracy Conventions §1–§9 + Reusable Primitives table — ≤30% prose reduction; **all 9 rules and the primitives table preserved verbatim**
- Port Configuration — verbatim
- Environment Variables — compressed; pointer to `.env.example` for full list
- Security Features — compressed to bullets (rate limits + production deployment + headers)
- Database Schema Notes — verbatim
- Common Issues — verbatim

**Sections retained as compressed summaries (the heavy compression cases):**
- **Recent Updates (v2.11)** — compressed from ~120 lines to ~30 lines. **Must preserve inline:**
  - `Organization.is_demo` flag exists for demo tenants
  - **Three-serializer-paths gotcha**: `is_demo` flows through `OrganizationSerializer.is_demo`, `UserOrganizationMembershipSerializer.organization_is_demo`, AND `UserProfileSerializer.organization_is_demo` — Claude must update all three when extending the field
  - Admin "Export seeded dataset as ZIP" action (superuser-gated, demo-org-only)
  - Drift-guard test in `test_admin_export.py::TestColumnDriftGuard`
  - Detailed v2.11 implementation history → `docs/CHANGELOG.md`
- **Previous Updates (v2.10)** — compressed from ~95 lines to ~25 lines. **Must preserve inline:**
  - Versatex brand color scheme exists (third option alongside navy/classic) — implementation history → `docs/CHANGELOG.md`
  - **Three-whitelist gotcha for adding any new color scheme**: TypeScript union, backend `ChoiceField`, runtime `saveSettingsToStorage` whitelist
  - Demo data seeding shipped (industry profiles) — full reference → `docs/DEMO_DATA.md`

**Sections added:**
- **Module-Specific Context** — pointer block listing canonical docs in Layer 3
- **External References** — pointer block listing relevant `docs/` files
- **Deployment** — ~10-line subsection pointing to Railway walkthrough

**Sections deleted (drift-prone or rediscoverable):**
- Full P2P API endpoint enumerations (~85 lines) — discoverable in `apps/analytics/p2p_urls.py`
- Full AI Insights API enumerations, both copies (~130 lines, includes deduplication of the v2.6 + v2.9 duplicate) — discoverable in `apps/analytics/urls.py`
- Test counts and file inventories with specific numbers (~80 lines) — rots on every CI run; regrowable via `pytest --collect-only`
- Frontend hook name listings (~70 lines) — discoverable in `frontend/src/hooks/`
- Versatex brand color scheme implementation tables (3-whitelist details, files-touched table — ~30 lines from v2.10) — gotcha summary preserved inline; full implementation history → `docs/CHANGELOG.md`
- v2.11 / v2.10 narrative prose around the surfaced gotchas (~150 lines combined) — gotchas surface inline; full narrative → `docs/CHANGELOG.md`

**Sections moved out:**
- P2P module architectural gotchas → `docs/claude/p2p.md`
- AI Insights conventions + LLM pipeline → `docs/claude/ai-insights.md`
- v2.0–v2.9 *rationale only* (the "why" decisions, not feature inventories) → `docs/CHANGELOG.md`
- v2.10 / v2.11 narrative prose around the inline-surfaced gotchas → `docs/CHANGELOG.md` (the gotchas themselves stay inline per "Sections retained as compressed summaries" above)
- "Creating Admin Users" shell commands → linked to existing `docs/onboarding/ASSIGN_USER_TO_ORGANIZATION.md`

**Target metrics:**
- 1,373 lines → ~380 lines
- 70,600 chars → ~18,000 chars (-74%)

### Layer 2 — Breadcrumb files

Two new files, each ≤15 lines. Co-located with the code they describe so Claude Code's parent-directory auto-discovery loads them when relevant.

**`backend/apps/procurement/CLAUDE.md`:**
```markdown
# Procurement App — Claude Context Pointer

You're working in the procurement app, which holds:
- Core data models: `Supplier`, `Category`, `Transaction`, `DataUpload`
- P2P models: `PurchaseRequisition`, `PurchaseOrder`,
  `GoodsReceipt`, `Invoice`

If your task touches any P2P model or workflow, read
**[../../../docs/claude/p2p.md](../../../docs/claude/p2p.md)** first —
it documents architectural invariants, the canonical primitives, and
known divergences you must not "fix".

For accuracy conventions affecting all analytics, see root CLAUDE.md
§ "Analytics accuracy conventions" and `docs/ACCURACY_AUDIT.md`.
```

**`backend/apps/analytics/CLAUDE.md`:**
```markdown
# Analytics App — Claude Context Pointer

You're working in the analytics app, which contains:
- Core procurement analytics: `services.py`, `services/*.py`
- P2P analytics: `p2p_services.py`, `p2p_views.py`, `p2p_urls.py`
- AI Insights + LLM: `ai_services.py`, `rag_services.py`, embeddings,
  semantic cache, streaming chat

Module-specific gotchas (read when relevant):
- P2P work → **[../../../docs/claude/p2p.md](../../../docs/claude/p2p.md)**
- AI Insights / LLM / RAG / streaming → **[../../../docs/claude/ai-insights.md](../../../docs/claude/ai-insights.md)**

For accuracy conventions affecting all analytics, see root CLAUDE.md
§ "Analytics accuracy conventions" and `docs/ACCURACY_AUDIT.md`.
```

### Layer 3 — Canonical Claude-tailored docs

Two new files using the structural template below.

**Template:**
```markdown
# <Module Name> — Claude Reference

> **When to read this:** [Specific trigger]
> **You can skip this if:** [Counter-trigger]

## Core invariants
[5-10 bullets, each citing the file/line where the rule is enforced]

## Primitives — use these, don't re-implement
[Table: Primitive | Location | Purpose]

## Known divergences (and why they exist)
[Things that look wrong but are intentional]

## Cross-cutting gotchas
[Multi-step traps that bite Claude on first attempt]

## API surface (orientation only)
[One paragraph pointing at urls.py — NO endpoint enumerations]

## Test patterns
[Where tests live, factory fixtures, standard test class pattern.
NO test counts.]

## See also
- Source-of-truth code paths
- Related ACCURACY_AUDIT.md anchors
- Related docs/CHANGELOG.md entries
```

**`docs/claude/p2p.md` content focus** (~120 lines):
- Document chain order invariant: PR → PO → GR → Invoice → Payment
- `P2PAnalyticsService` does NOT inherit from `BaseAnalyticsService` (intentional, tracked in ACCURACY_AUDIT Cross-Module Open)
- `P2PAnalyticsService._avg_days_to_pay` is the canonical primitive (8 call sites consolidated)
- 3-way matching: `Invoice.match_status='exception'` flow, never delete on mismatch
- All endpoints scope by `request.organization` — tenant isolation invariant
- `P2PImportMixin` location for admin CSV import + drift-guard test in `test_admin_export.py`
- API surface: orientation pointer to `apps/analytics/p2p_urls.py`
- Test patterns: `pytest apps/reports/tests/test_p2p_generators.py` etc.

**`docs/claude/ai-insights.md` content focus** (~140 lines):
- §6 no-silent-fallback rule (deterministic vs enhanced labeling)
- `AIInsightsService.deduplicate_savings` primitive (instance method at `ai_services.py:873`)
- `LLMRequestLog`, `SemanticCache`, `EmbeddedDocument` model purposes
- Prompt caching strategy + 90% cost reduction on cached reads
- Semantic cache 0.90 similarity threshold
- RAG ingest paths and refresh schedule
- Streaming chat SSE protocol
- Celery Beat schedule (overnight batch generation, cleanup)
- Hallucination prevention validation layer
- API surface: orientation pointer to `apps/analytics/ai_*.py` and `rag_*.py`
- Test patterns: where AI tests live

### Layer 4 — Existing reference docs (unchanged, newly linked)

| File | Why linked from root |
|---|---|
| `docs/ACCURACY_AUDIT.md` | 9-convention ledger, Cross-Module Open tracker |
| `docs/DEMO_DATA.md` | Industry profiles + seed command reference |
| `docs/RAILWAY-DEPLOY-WALKTHROUGH.md` | Production deployment runbook |
| `docs/FIRST-DEPLOY-WALKTHROUGH.md` | Hetzner alternative deployment runbook |
| `docs/deployment/*` | DEPLOY-PLAYBOOK, MONITORING, CLOUDFLARE-EDGE runbooks |
| `docs/setup/QUICK_START_GUIDE.md` | First-time setup |
| `docs/setup/DOCKER-TROUBLESHOOTING.md` | Docker issue lookup |
| `docs/setup/WINDOWS-SETUP.md` | Windows-specific setup |
| `docs/onboarding/ASSIGN_USER_TO_ORGANIZATION.md` | Replaces "Creating Admin Users" shell snippet |
| `docs/onboarding/TENANT_PROVISIONING.md` | Multi-tenancy onboarding |
| `docs/CHANGELOG.md` (NEW) | Curated v2.0–v2.9 rationale |

### Layer 5 — Files deleted

| File | Reason |
|---|---|
| `docs/development/CLAUDE.md` | Actively wrong (port 8001 vs reality 8002, pre-rebrand project name `analytics-dashboard-fullstack-7`, missing v2.5–v2.11 features). Net-negative — better removed than misleading. Git history preserves it. |

## Data Flow

Documentation refactor — no runtime data flow. The "data" being moved is text content from root `CLAUDE.md` to its new destinations. Git history preserves the original at any commit prior to Commit 2.

## Migration Sequence

Three commits, one session.

### Commit 1 — Additive: create new files (zero risk)

1. Extract first (copy out, do not delete from root yet):
   - P2P architectural content → `docs/claude/p2p.md`
   - AI Insights conventions → `docs/claude/ai-insights.md`
   - v2.0–v2.9 *rationale only* → `docs/CHANGELOG.md`
2. Create breadcrumbs:
   - `backend/apps/procurement/CLAUDE.md`
   - `backend/apps/analytics/CLAUDE.md`
3. Verify all 5 new files exist; lint markdown; check no broken cross-references.

**Commit message:** `docs(claude): add docs/claude/ canonical refs + app breadcrumbs + CHANGELOG`

### Commit 2 — Substantive: rewrite root CLAUDE.md

1. Cut sections marked "delete" or "moved" (per Components > Layer 1 above).
2. Compress Analytics Accuracy Conventions §1–9 (~30% prose reduction; preserve all 9 rules + primitives table verbatim).
3. Compress Security/Schema/Common Issues sections.
4. Add new "Module-Specific Context" pointer block (~15 lines).
5. Add new "External References" pointer block (~10 lines).
6. Add new "Deployment" subsection (~10 lines).
7. Verify size targets and content preservation (see Verification).

**Commit message:** `docs(claude): trim root CLAUDE.md from 70k→18k chars (-74%)`

### Commit 3 — Cleanup

1. Delete `docs/development/CLAUDE.md`.
2. Append "Documentation audit candidates" section to `docs/TECHNICAL_DEBT.md` listing the 6 uncertain docs.

**Commit message:** `docs(claude): delete stale docs/development/CLAUDE.md + flag audit candidates`

## Verification

### Mechanical checks (after Commit 2)

```bash
# Size targets
wc -c CLAUDE.md                              # Expect: < 20,000 chars
wc -l CLAUDE.md                              # Expect: ~380 lines

# Cross-reference integrity
grep -oE '\[.*?\]\(([^)]+\.md[^)]*)\)' CLAUDE.md | \
  grep -oE '\([^)]+\)' | tr -d '()' | \
  while read f; do test -f "$f" || echo "MISSING: $f"; done

# Section structure sanity
grep -c "^## " CLAUDE.md                     # Expect: ~12-15 sections
grep -c "^### " CLAUDE.md                    # Expect: ~20-30 subsections
```

### Content preservation check

```bash
# All 9 accuracy conventions survived
grep -E "^### [0-9]\." CLAUDE.md | head -20

# Primitives table survived
grep -A 10 "Reusable primitives" CLAUDE.md

# Spot-check key invariants
grep "BACKEND_PORT" CLAUDE.md
grep "ALLOWED_PREFERENCE_KEYS" CLAUDE.md
grep "is_demo" CLAUDE.md
```

### Functional smoke test (next session)

1. Open `backend/apps/analytics/p2p_services.py` in a fresh Claude Code session.
2. Confirm via session-start banner that `backend/apps/analytics/CLAUDE.md` was auto-discovered.
3. Ask Claude a P2P-specific question; observe whether it reads `docs/claude/p2p.md` when relevant.

### Acceptance criteria

| Criterion | Pass condition |
|---|---|
| Size reduction | Root CLAUDE.md < 20k chars |
| Threshold compliance | No "Large CLAUDE.md" performance warning |
| Link integrity | All `docs/` links resolve to existing files |
| Accuracy conventions intact | All 9 rules + primitives table present in root |
| Module gotchas accessible | `docs/claude/p2p.md` and `docs/claude/ai-insights.md` exist with template structure |
| Auto-discovery works | Editing `apps/analytics/*.py` triggers breadcrumb load |
| No content lost silently | Critical invariants greppable in root or canonical docs |

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Root rewrite drops content someone relied on | Low | Low | Git history preserves; can cherry-pick back |
| Breadcrumb auto-discovery doesn't fire as expected | Low | Medium | Smoke test in next session; if it fails, fall back to explicit pointers in root CLAUDE.md |
| Curated CHANGELOG loses subtlety from original prose | Medium | Low | Original CLAUDE.md prose lives in git history forever |
| User wants to revert | Low | Low | `git revert` of all 3 commits in sequence — clean rollback |
| Breadcrumbs themselves bloat (over-15-lines) | Medium | Low | Hard cap at 15 lines per breadcrumb, enforced in review |

## Open Questions

None at design close. All clarifying questions answered during brainstorming session.

## Decisions Log

| # | Decision | Choice |
|---|---|---|
| Q1 | Audience strategy for split | (C) Hybrid — reuse Claude-friendly existing docs, create new for user-facing/missing |
| Q2 | Disposition of uncertain docs (`AI_INSIGHTS - v1.0.md`, `SECURITY_AUDIT_REPORT.md`) | (A) Out-of-scope; flag in `TECHNICAL_DEBT.md` |
| Q3 | Granularity | (A) Coarse — 2 new files (`p2p.md`, `ai-insights.md`) |
| Q4 | Discovery mechanism | (C) Hybrid — breadcrumbs + canonical docs + root pointer |
| Q5.1 | v2.0–v2.9 changelog disposition | (ii) Selective — keep "why" decisions in CHANGELOG, delete obvious feature lists |
| Q5.2 | Reports module disposition | (i) Delete + compress to bullets in root |
