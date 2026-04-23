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
