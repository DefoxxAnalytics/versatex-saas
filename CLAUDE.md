# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Versatex Analytics - An enterprise-grade procurement analytics platform with organization-based multi-tenancy.

**Tech Stack:**
- Backend: Django 5.0 + Django REST Framework + PostgreSQL + Celery/Redis
- Frontend: React 18 + TypeScript + Tailwind CSS 4 + Vite
- Auth: JWT tokens with role-based access (admin, manager, viewer)

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
docker-compose exec backend python manage.py test
docker-compose exec backend python manage.py test apps.authentication  # specific app
docker-compose exec backend python manage.py test apps.authentication.tests.TestLoginView  # specific test class
docker-compose exec backend python manage.py test apps.authentication.tests.TestLoginView.test_valid_login  # specific test method

# Frontend tests
cd frontend
pnpm test           # watch mode
pnpm test:run       # single run
pnpm test:ui        # with UI
pnpm test:run src/components/__tests__/Button.test.tsx  # specific test file
```

### Demo Data Seeding

Populate any organization with realistic, industry-specific demo data end-to-end. Full reference in [docs/DEMO_DATA.md](docs/DEMO_DATA.md).

```bash
# Healthcare: base layer + P2P/contracts/policies
docker-compose exec backend python manage.py seed_industry_data --industry healthcare --org-slug uch --wipe
docker-compose exec backend python manage.py seed_demo_data --org uch --industry healthcare --wipe

# Higher Education
docker-compose exec backend python manage.py seed_industry_data --industry higher-ed --org-slug tsu --wipe
docker-compose exec backend python manage.py seed_demo_data --org tsu --industry higher-ed --wipe

# Generic (Manufacturing) - existing org with Transactions already loaded
docker-compose exec backend python manage.py seed_demo_data --org eaton --wipe
```

Both commands are idempotent via `--wipe` and deterministic via `--seed` (default 42). See [backend/apps/procurement/management/commands/_industry_profiles.py](backend/apps/procurement/management/commands/_industry_profiles.py) to add new industries.

### Type Checking & Linting

```bash
# Frontend
cd frontend
pnpm check          # TypeScript check (tsc --noEmit)
pnpm format         # Prettier format
pnpm format --check # Check formatting without changes

# Backend (install dev deps first: pip install black isort flake8)
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
│   ├── authentication/     # User, Organization, UserProfile, UserOrganizationMembership, AuditLog models
│   │   ├── organization_utils.py  # Shared org utilities (get_target_organization, user_can_access_org)
│   ├── procurement/        # Supplier, Category, Transaction, DataUpload + P2P models (PR, PO, GR, Invoice)
│   ├── analytics/          # AnalyticsService + P2PAnalyticsService - all analytics calculations
│   │   ├── services.py     # Core procurement analytics
│   │   ├── p2p_services.py # P2P analytics (cycle, matching, aging, requisitions, POs, payments)
│   │   ├── p2p_views.py    # P2P API endpoints
│   │   └── p2p_urls.py     # P2P URL routing
│   └── reports/            # Report generation, scheduling, and export
│       ├── generators/     # 13 report generators (including 3 P2P: pr_status, po_compliance, ap_aging)
│       ├── renderers/      # PDF (ReportLab), Excel (openpyxl), CSV (pandas)
│       └── tasks.py        # Celery tasks for async generation
├── config/                 # Django settings, URLs, Celery config
└── templates/admin/        # Custom Django admin templates (navy theme)
```

**Key Patterns:**
- All data models are scoped by `organization` ForeignKey for multi-tenancy
- `AnalyticsService` class in `apps/analytics/services.py` handles all analytics calculations
- `P2PAnalyticsService` class in `apps/analytics/p2p_services.py` handles P2P analytics
- JWT auth via djangorestframework-simplejwt with token refresh
- CSRF exempt on LoginView for frontend API calls
- Celery worker for background tasks (CSV processing, reports)

### Frontend Structure (`frontend/src/`)

```
src/
├── components/
│   ├── ui/                 # shadcn/ui components (Radix primitives)
│   ├── DashboardLayout.tsx # Main layout with sidebar navigation
│   └── ProtectedRoute.tsx  # Auth guard component
├── contexts/
│   ├── AuthContext.tsx     # Auth state (isAuth, checkAuth, logout)
│   ├── OrganizationContext.tsx  # Multi-org support (activeOrg, switchOrganization)
│   └── ThemeContext.tsx    # Light/dark theme
├── hooks/
│   ├── useAnalytics.ts     # Analytics data fetching
│   ├── useP2PAnalytics.ts  # P2P analytics data fetching
│   ├── useFilters.ts       # Filter state management
│   ├── useProcurementData.ts # Transaction data fetching
│   └── useReports.ts       # Report generation, scheduling, downloads
├── lib/
│   ├── api.ts              # Axios client with auth interceptors
│   ├── auth.ts             # Auth API functions
│   └── analytics.ts        # Analytics calculations (client-side)
└── pages/                  # Route components (lazy-loaded)
```

**Key Patterns:**
- Wouter for routing (not React Router)
- TanStack Query v5 for server state management
- shadcn/ui components built on Radix primitives
- All pages lazy-loaded for code splitting
- Auth state in localStorage (`access_token`, `refresh_token`, `user`)
- Admin panel link only shown when `user.profile.role === 'admin'`
- Axios interceptors handle JWT token refresh automatically

### API Structure

```
/api/v1/auth/          # login, register, logout, token/refresh, user, change-password
/api/v1/procurement/   # suppliers, categories, transactions (CRUD + upload_csv, bulk_delete, export), uploads
/api/v1/analytics/     # overview, spend-by-category, spend-by-supplier, pareto, tail-spend, monthly-trend, stratification, seasonality, year-over-year, consolidation
/api/v1/analytics/ai-insights/  # AI insights, feedback, ROI tracking, deep analysis (see AI Insights below)
/api/v1/analytics/p2p/ # P2P analytics: cycle, matching, aging, requisitions, purchase-orders, supplier-payments
/api/v1/reports/       # Report generation, scheduling, and downloads (see Reports Module below)
```

Legacy endpoints (`/api/auth/`, `/api/procurement/`, `/api/analytics/`) are supported for backwards compatibility.

**Frontend API Client:** All API calls use typed interfaces in `frontend/src/lib/api.ts`. This file contains `authAPI`, `procurementAPI`, `analyticsAPI`, and `reportsAPI` objects with typed request/response interfaces.

## Port Configuration

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8001/api` (maps to container port 8000)
- Django Admin: `http://localhost:8001/admin`
- API Docs: `http://localhost:8001/api/docs` (interactive API documentation)
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Required
SECRET_KEY=your-django-secret-key  # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=True  # Set to False in production
DB_PASSWORD=your_password

# Frontend
VITE_API_URL=http://127.0.0.1:8001/api
```

See `.env.example` for the full list of configuration options and the production security checklist.

## Security Features

### Rate Limiting
- Uploads: 10/hour per user
- Exports: 30/hour per user
- Bulk deletes: 10/hour per user
- Login attempts: 5/minute
- Anonymous: 100/hour
- Authenticated: 1000/hour

### Production Deployment

Use the production Docker Compose override for enhanced security:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production features:
- No external ports for DB/Redis (internal network only)
- Redis authentication enabled
- DEBUG=False enforced
- HTTPS-only CORS origins
- Resource limits on containers
- Read-only filesystem on frontend
- `no-new-privileges:true` security option

### Security Headers (Nginx)

The frontend nginx configuration (`frontend/nginx/nginx.conf`) includes comprehensive security headers:

```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=()
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; ...
```

### Production Checklist

Before deploying to production, complete these steps:

```bash
# 1. Generate new SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 2. Set environment variables
DEBUG=False
ALLOWED_HOSTS=your-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend.com
CSRF_TRUSTED_ORIGINS=https://your-frontend.com

# 3. Deploy with production compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Verify security headers
curl -I https://your-frontend.com
```

## Database Schema Notes

- `Organization` - multi-tenant root, all data scoped to org
- `UserProfile` - extends Django User with org, role (admin/manager/viewer)
- `UserOrganizationMembership` - many-to-many between User and Organization with per-org role (supports multi-org users)
- `Transaction` - core data model with supplier/category FKs, amount, date
- `DataUpload` - tracks CSV upload history with batch_id

### P2P Models (in `apps/procurement/models.py`)
- `PurchaseRequisition` - PR with status, department, cost center, approval workflow
- `PurchaseOrder` - PO linked to supplier, with amounts, contract backing, amendments
- `GoodsReceipt` - GR linked to PO, with quantity received/accepted
- `Invoice` - Invoice with matching status, payment terms, exception handling

## Creating Admin Users

```bash
# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Then in Django shell, create profile:
docker-compose exec backend python manage.py shell
>>> from apps.authentication.models import Organization, UserProfile
>>> from django.contrib.auth.models import User
>>> org = Organization.objects.create(name='Default Org', slug='default')
>>> user = User.objects.get(username='admin')
>>> UserProfile.objects.create(user=user, organization=org, role='admin', is_active=True)
```

## Common Issues

**Login 403/500 errors:** User needs a UserProfile with organization and active status.

**Frontend changes not reflecting:** Run `docker-compose up -d --build --force-recreate frontend`

**Static files missing in admin:** Run `collectstatic` command.

**Port 8001 in use:** Check for WSL relay processes; can change in docker-compose.yml.

## CI/CD

GitHub Actions workflow runs on push/PR to master:
- Backend: Python linting (black, isort, flake8), Django tests with PostgreSQL/Redis services
- Frontend: TypeScript check, Prettier format check, Vitest tests, production build
- Docker: Build verification for both backend and frontend images
- Security: Trivy vulnerability scanning

Badges:
- [![CI](https://github.com/DefoxxAnalytics/versatex-analytics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/DefoxxAnalytics/versatex-analytics/actions/workflows/ci.yml)

## Test Coverage

### Backend Tests (621 tests, 70% coverage)

```bash
# Run all backend tests
docker-compose exec backend pytest --cov=apps --cov-report=term-missing

# Run specific app tests
docker-compose exec backend pytest apps/reports/tests/ -v
docker-compose exec backend pytest apps/procurement/tests/ -v
docker-compose exec backend pytest apps/analytics/tests/ -v
docker-compose exec backend pytest apps/authentication/tests/ -v
```

#### Test Structure

| App | Test Files | Tests | Coverage |
|-----|------------|-------|----------|
| **reports** | 4 files | ~180 | 85%+ |
| **procurement** | 3 files | ~150 | 80%+ |
| **analytics** | 2 files | ~120 | 75%+ |
| **authentication** | 2 files | ~170 | 70%+ |

#### Reports App Test Files (`backend/apps/reports/tests/`)

| File | Description | Test Count |
|------|-------------|------------|
| `test_views.py` | Report API endpoints, permissions, CRUD operations | ~45 |
| `test_generators.py` | Core report generators (executive, spend, pareto, etc.) | ~40 |
| `test_p2p_generators.py` | P2P report generators (PR status, PO compliance, AP aging) | ~40 |
| `test_renderers.py` | PDF, Excel, CSV rendering with branding | ~55 |
| `test_tasks.py` | Celery async tasks (generate, schedule, cleanup) | ~23 |

#### Key Test Patterns

**API View Tests:**
```python
@pytest.mark.django_db
class TestReportViewSet:
    def test_list_reports_authenticated(self, api_client, user, organization):
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/reports/')
        assert response.status_code == 200
```

**Generator Tests:**
```python
@pytest.mark.django_db
class TestSpendAnalysisGenerator:
    def test_generate_with_data(self, organization, transactions):
        generator = SpendAnalysisReportGenerator(organization)
        data = generator.generate()
        assert 'summary' in data
        assert 'spend_by_category' in data
```

**Celery Task Tests:**
```python
@pytest.mark.django_db
class TestGenerateReportAsync:
    @patch('apps.reports.services.ReportingService')
    def test_successful_generation(self, mock_service_class, report):
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        result = generate_report_async(str(report.pk))
        assert result['status'] == 'completed'
```

**PDF Renderer Tests:**
```python
@pytest.mark.django_db
class TestPDFRendererReportTypes:
    def test_executive_summary_pdf(self, organization, admin_user):
        renderer = PDFReportRenderer(organization)
        data = {'summary': {...}, 'insights': [...]}
        pdf_bytes = renderer.render('executive_summary', data)
        assert pdf_bytes.startswith(b'%PDF')
```

### Frontend Tests (866 tests)

```bash
# Run all frontend tests
cd frontend
pnpm test:run --coverage

# Run specific test files
pnpm test:run src/pages/__tests__/Suppliers.test.tsx
pnpm test:run src/hooks/__tests__/
```

#### Test Structure

| Category | Test Files | Tests |
|----------|------------|-------|
| **Pages** | 5 files | ~80 |
| **Hooks** | 10 files | ~200 |
| **Components** | 8 files | ~150 |
| **Contexts** | 4 files | ~50 |
| **Lib** | 4 files | ~100 |
| **Other** | Various | ~286 |

#### Key Frontend Test Files

| File | Description |
|------|-------------|
| `pages/__tests__/Suppliers.test.tsx` | Supplier list, search, HHI risk indicators |
| `pages/__tests__/Settings.test.tsx` | Profile form, theme, notifications, AI settings |
| `pages/__tests__/Overview.test.tsx` | Dashboard stats, skeleton loaders, charts |
| `hooks/__tests__/useFilters.test.ts` | Filter state management |
| `hooks/__tests__/useProcurementData.test.ts` | Procurement data fetching |

### Running Tests with Coverage

```bash
# Backend: Full coverage report
docker-compose exec backend pytest --cov=apps --cov-report=html
# View at: backend/htmlcov/index.html

# Frontend: Full coverage report
cd frontend
pnpm test:run --coverage
# View at: frontend/coverage/index.html
```

### Test Configuration Files

- **Backend**: `backend/pytest.ini`, `backend/conftest.py`
- **Frontend**: `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`
- **MSW Handlers**: `frontend/src/test/mocks/handlers.ts` (API mocking)

## Recent Updates (v2.11)

### `Organization.is_demo` — synthetic-tenant flag (end-to-end)

A first-class BooleanField on `Organization` that marks any tenant containing seeded/synthetic data, so superusers can distinguish demo orgs from real customer orgs at a glance and so data-governance actions can gate on it.

#### Migration

[`0010_add_is_demo_to_organization.py`](backend/apps/authentication/migrations/0010_add_is_demo_to_organization.py) — `AddField` + reversible `RunPython` backfilling `is_demo=True` for the canonical demo slugs (`eaton`, `uch`, `tsu`). The seed commands now set the flag automatically on create/update, so future industry profiles inherit it without touching the migration.

#### API surface

The flag flows through **three** paths because `OrganizationSwitcher` synthesises `Organization` objects from memberships on one branch and hits `/auth/organizations/` on the other:

| Serializer | Field | Used by |
|---|---|---|
| `OrganizationSerializer` | `is_demo` (read-only) | `/api/v1/auth/organizations/` (superuser switcher) |
| `UserOrganizationMembershipSerializer` | `organization_is_demo` (source-derived, read-only) | `/api/v1/auth/user/organizations/`, nested in `UserProfileSerializer.organizations` |
| `UserProfileSerializer` / `UserProfileWithOrgsSerializer` | `organization_is_demo` (source-derived, read-only) | Legacy single-org fallback path in `OrganizationContext` |

All three fields are read-only — only admin (Django admin) or the seed commands can flip the flag.

#### Frontend

- `Organization.is_demo: boolean` added to [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts)
- `OrganizationMembership.organization_is_demo: boolean` and `UserProfile.organization_is_demo?: boolean` added alongside
- [`OrganizationContext.tsx`](frontend/src/contexts/OrganizationContext.tsx) synthetic `Organization` constructions (3 sites: primary-membership, profile fallback, memberOrgs map) now carry the flag
- [`OrganizationSwitcher.tsx`](frontend/src/components/OrganizationSwitcher.tsx):
  - Amber `FlaskConical` + **"Demo"** `Badge` next to the Primary star in each dropdown row (`aria-label="Synthetic demo data"`)
  - Amber ring (`ring-1 ring-amber-400/60`) on the trigger button when the active org is demo — visible without opening the dropdown. Orthogonal to the existing "viewing other org" amber tint: one axis is *whose* data, the other is *what kind of* data.

#### Django admin

[`OrganizationAdmin`](backend/apps/authentication/admin.py) gained:
- `is_demo` in the root fieldset (editable)
- `is_demo` on `list_filter`
- A `demo_badge` column rendering an amber `DEMO` chip via `format_html` (mirrors the existing `member_count` display-method pattern)
- Removed a stale `ai_settings` fieldset that referenced a non-existent field (was a lingering reference from the v2.9 plan; `ai_settings` actually lives inside `UserProfile.preferences` JSON)

### Demo organization rename: Eaton → Bolt & Nuts Manufacturing

The slug (`eaton`) is preserved — it's referenced by the `0010` migration backfill tuple, by `OrganizationContext`'s `localStorage` keys, and by all `--org eaton` doc examples. Only the display `name` field changed. The CLAUDE.md Demo Organization Inventory table was updated in-place; all seed commands continue to pass `--org-slug eaton` unchanged.

Bolt & Nuts was then fully reseeded from scratch via the manufacturing industry profile:

```bash
docker-compose exec backend python manage.py seed_industry_data \
    --industry manufacturing --org-slug eaton --org-name "Bolt & Nuts Manufacturing" --wipe
docker-compose exec backend python manage.py seed_demo_data \
    --org eaton --industry manufacturing --wipe
```

Result: 100% synthetic dataset — 25,000 transactions ($787M total spend), 576 named manufacturing suppliers (DMG Mori, Haas Automation, Makino, ABB Robotics, Fanuc, Mazak, Okuma, etc.), 15 categories, 80 contracts, 4 policies, 150 violations, 500 PRs, 400 POs, 287 GRs, 287 invoices. The two original CSV uploads (`vstx-etn.csv`, `procurement_sample.csv`) and their `DataUpload` audit rows were purged. `upload_batch` on seeded P2P uses the `seed-XXXX` prefix from `seed_demo_data.py:92`.

### Admin action: "Export seeded dataset as ZIP"

Closes the round-trip loop opened by the existing admin Import CSV buttons. Lets a superuser snapshot any `is_demo=True` org and re-import it anywhere.

#### UX

`/admin/authentication/organization/` → select demo org(s) → **Actions → "Export seeded dataset as ZIP (demo orgs only)" → Go**. Downloads `seeded-datasets-YYYYMMDD-HHMMSS.zip` containing one `<slug>-dataset.zip` per selected org, each containing 10 CSVs + `README.txt` in a `<slug>/` folder.

#### Three-tier round-trip taxonomy

| Tier | Models | Importer | Columns |
|---|---|---|---|
| **A** — admin Import CSV | `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `Invoice` | `P2PImportMixin` ([procurement/admin.py:1334](backend/apps/procurement/admin.py)) | Mirror `p2p_import_fields` verbatim |
| **B** — DataUpload wizard | `Transaction` | `CSVProcessor` ([procurement/services.py:93](backend/apps/procurement/services.py)) | `REQUIRED_COLUMNS` + `OPTIONAL_COLUMNS` exactly (no column-mapping step needed) |
| **C** — reference only | `Supplier`, `Category`, `Contract`, `SpendingPolicy`, `PolicyViolation` | n/a | Natural model-field columns; regenerate via `seed_demo_data` |

A **drift-guard test** ([`test_admin_export.py::TestColumnDriftGuard`](backend/apps/authentication/tests/test_admin_export.py)) diff-checks the exporter column constants against the two importer source-of-truth modules on every CI run — anyone editing `p2p_import_fields` or `CSVProcessor.REQUIRED_COLUMNS` without updating the exporter gets a loud test failure before round-trip silently breaks.

#### Gating

- `OrganizationAdmin.get_actions()` hides the action entirely from non-superusers (invisible, not merely blocked)
- Action body re-checks `request.user.is_superuser` defensively
- Rejects the **entire** queryset with `messages.error` if any selected org has `is_demo=False` — no silent partial export

#### Audit trail

Every export writes one `AuditLog` row per org via the existing [`log_action()`](backend/apps/authentication/utils.py) helper:

```python
log_action(
    user=request.user,
    action='export',
    resource='organization_dataset',
    resource_id=org.slug,
    details={
        'organization_name': org.name,
        'is_demo': org.is_demo,
        'row_counts': json.dumps(counts, sort_keys=True),  # dict value types disallowed → JSON string
        'zip_bytes': len(payload),
    },
    request=request,
)
```

Three new keys were added to [`AuditLog.ALLOWED_DETAIL_KEYS`](backend/apps/authentication/models.py): `is_demo`, `row_counts`, `zip_bytes`. The `organization_name` and `export` action were already allowed.

#### Files shipped

| Layer | Path | Purpose |
|---|---|---|
| Export helper (new) | [`backend/apps/authentication/admin_export.py`](backend/apps/authentication/admin_export.py) | Column constants (3 tiers), per-model row generators, `build_org_zip()` |
| Admin action | [`backend/apps/authentication/admin.py`](backend/apps/authentication/admin.py) | `export_demo_datasets` action + `get_actions()` override on `OrganizationAdmin` |
| Model | [`backend/apps/authentication/models.py`](backend/apps/authentication/models.py) | 3 new `AuditLog.ALLOWED_DETAIL_KEYS` entries |
| Factory | [`backend/apps/authentication/tests/factories.py`](backend/apps/authentication/tests/factories.py) | `DemoOrganizationFactory(OrganizationFactory)` with `is_demo=True` |
| Tests (new) | [`backend/apps/authentication/tests/test_admin_export.py`](backend/apps/authentication/tests/test_admin_export.py) | 10 tests: zip shape, column drift guard, non-demo rejection, non-superuser visibility, AuditLog assertion |

Performance envelope: Bolt & Nuts (25K transactions) assembles a 311 KB compressed zip in ~1 s. No streaming or Celery needed at current seed sizes.

## Previous Updates (v2.10)

### Versatex Brand Color Scheme

A third `colorScheme` option — `"versatex"` — has been added alongside the existing `"navy"` and `"classic"` schemes. Based on the official brand guide (`BrandGuidelines2.png`): grayscale chrome (100% / 80% / 40% black + white) with the signature yellow `#FDC00F` (PMS 1235 C) used as an accent — primary buttons stay charcoal-gray, yellow lights up sidebar selection, focus rings, the user avatar, and chart series.

#### Files touched

| Layer | File | Change |
|-------|------|--------|
| Design tokens | [frontend/src/index.css](frontend/src/index.css) | `.versatex` and `.versatex.dark` CSS variable blocks (OKLCH) |
| Theme toggle | [frontend/src/contexts/ThemeContext.tsx](frontend/src/contexts/ThemeContext.tsx) | Apply `.versatex` class to `document.documentElement` |
| Type + storage | [frontend/src/hooks/useSettings.ts](frontend/src/hooks/useSettings.ts) | Widen `ColorScheme` union and fix runtime whitelist in `saveSettingsToStorage` |
| API types | [frontend/src/lib/api.ts](frontend/src/lib/api.ts) | Widen `UserPreferences.colorScheme` |
| Settings UI | [frontend/src/pages/Settings.tsx](frontend/src/pages/Settings.tsx) | Third dropdown option with yellow-on-black swatch |
| Layout | [frontend/src/components/DashboardLayout.tsx](frontend/src/components/DashboardLayout.tsx) | Refactored `getHeaderStyles` / `getSidebarStyles` from nested ternaries to a per-scheme lookup map; added versatex branch |
| Charts | [frontend/src/components/Chart.tsx](frontend/src/components/Chart.tsx) | `VERSATEX_CHART_PALETTE` + `VERSATEX_AREA_GRADIENT`; when scheme is versatex, strips hardcoded `itemStyle.color` from series and injects the palette via `option.color` so all charts lead with yellow |
| Backend | [backend/apps/authentication/serializers.py](backend/apps/authentication/serializers.py) | Extended `colorScheme` ChoiceField to accept `'versatex'` |

#### Three independent whitelists that had to be updated

Adding a new brand scheme required touching three separate validators that all had to accept `"versatex"` — if any one rejected, the value would silently revert to `"navy"`:

1. **TypeScript union** in `useSettings.ts` / `api.ts` — compile-time type
2. **Backend `ChoiceField`** in `serializers.py` — server-side 400 on invalid value
3. **Runtime guard** in `saveSettingsToStorage()` — silently coerces unknown values to default

#### Intentional carve-out

The Spend Distribution donut keeps red/yellow/green — those are **semantic risk tiers** (High / Medium / Low value), not decoration. Swapping to the brand palette would break the color affordance.

### Demo Data Seeding + Industry Profiles

Two new management commands stand up realistic, industry-specific demo environments end-to-end. Full guide in [docs/DEMO_DATA.md](docs/DEMO_DATA.md).

#### New Management Commands

| Command | Purpose |
|---------|---------|
| [`seed_industry_data`](backend/apps/procurement/management/commands/seed_industry_data.py) | Creates/renames an organization and populates the base layer — Categories, Suppliers, Transactions — using an industry profile (log-normal amount distribution per category, monthly seasonality, Pareto supplier weighting) |
| [`seed_demo_data`](backend/apps/procurement/management/commands/seed_demo_data.py) | Adds the P2P layer — Contracts, Spending Policies, Policy Violations, PRs, POs, GRs, Invoices — on top of an existing org with base data |

Both commands are idempotent via `--wipe` and deterministic via `--seed`.

#### Shipped Industry Profiles

Profile data lives in [`_industry_profiles.py`](backend/apps/procurement/management/commands/_industry_profiles.py) and is easy to extend.

| Profile | Default Org | Scale | Highlights |
|---------|-------------|-------|------------|
| `healthcare` | Mercy Regional Medical Center | ~$650M spend, 603 suppliers, 15 categories | GE Healthcare, Philips, Siemens Healthineers, Stryker, Cardinal Health, McKesson; 340B + GPO + Capital Approval + Value Analysis policies; ED/OR/ICU/Pharmacy/Radiology/Oncology departments; flu-season seasonality |
| `higher-ed` | Pacific State University | ~$1.68B spend, 541 suppliers, 16 categories | Turner Construction, Skanska, Thermo Fisher, Elsevier, Apple, Dell, Sodexo; NSF/NIH Grant Compliance + E&I/NASPO Consortium + PI Direct Purchase Limit + Capital Construction policies; Biology/Chemistry/Engineering/Library/Athletics departments; fiscal-year + semester seasonality |
| `manufacturing` | Apex Manufacturing Co. | ~$785M spend, 576 suppliers, 15 categories | DMG Mori, Haas Automation, Makino, Fanuc Robotics, ABB Robotics, Rockwell Automation, Nucor, Steel Dynamics, Fastenal, Grainger, Jabil, Flex; PPAP/ISO 9001 + Capital Authorization + Conflict Minerals + MRO Cap policies; Production/Maintenance/Quality/Engineering/Supply Chain/EHS/Tooling departments; July shutdown dip + December year-end capex spike |

#### Industry-Aware P2P Generation

`seed_demo_data` accepts `--industry {healthcare,higher-ed}` to swap in industry-specific:
- **Departments** (e.g., "Emergency Department" vs "Biology" vs generic "Operations")
- **Cost-center prefix** (`MRMC-0001` vs `PSU-0001` vs `CC-0001`)
- **Payment terms** (adds 2/10 Net 30 for healthcare)
- **Spending policies** (industry-appropriate: 340B/GPO vs federal-grant/consortium vs generic)

Omit `--industry` for generic/manufacturing defaults.

#### Bug Fix: Contract List Endpoint

[`apps/analytics/contract_services.py:get_contracts_list()`](backend/apps/analytics/contract_services.py) now returns `utilization_percentage` per contract. The Contracts page frontend called `.toFixed()` on this field; when the contracts table was empty the bug was invisible, but any populated org crashed the page. Fixed by joining supplier spend totals in the list serializer.

#### Security Fix: Nginx CSP

[`frontend/nginx/nginx.conf`](frontend/nginx/nginx.conf) removed invalid `connect-src` tokens (`https://api.*` and `wss://*`) that generated a CSP console error on every page load. The `*` wildcard is only valid at the start of a hostname, not as a TLD placeholder.

#### Demo Organization Inventory

| Org | Slug | Industry | Source |
|-----|------|----------|--------|
| Bolt & Nuts Manufacturing | `eaton` | Manufacturing | User CSV upload + `seed_demo_data` |
| Mercy Regional Medical Center | `uch` | Healthcare | `seed_industry_data` + `seed_demo_data` |
| Pacific State University | `tsu` | Higher Education | `seed_industry_data` + `seed_demo_data` |

---

## Previous Updates (v2.9)

### AI Insights Enhancement - Complete LLM-Powered Intelligence Platform

Major enhancement to the AI Insights module transforming it into a production-grade LLM-powered procurement intelligence platform with 7 complete phases.

#### New Features

| Feature | Description |
|---------|-------------|
| **Prompt Caching** | Anthropic prompt caching with 90% cost reduction on cached reads |
| **Semantic Caching** | pgvector-powered similarity search (0.90 threshold) for 73% fewer LLM calls |
| **RAG Document Intelligence** | Vector search for supplier profiles, contracts, and historical insights |
| **Streaming Chat** | Real-time SSE streaming for conversational AI interface |
| **LLM Usage Dashboard** | Cost tracking, cache efficiency metrics, and usage trends |
| **Batch Processing** | Overnight insight generation and enhancement via Celery Beat |
| **Hallucination Prevention** | Validation layer for monetary values, supplier names, and date ranges |

#### New Backend Models

```python
# In apps/analytics/models.py
LLMRequestLog        # Tracks all LLM API calls with tokens, cost, latency
SemanticCache        # pgvector embeddings for semantic similarity search
EmbeddedDocument     # RAG document store with vector embeddings
```

#### New API Endpoints

```
# LLM Usage & Cost Tracking
GET  /api/v1/analytics/ai-insights/usage/           # Usage summary (requests, cost, cache hit rate)
GET  /api/v1/analytics/ai-insights/usage/daily/     # Daily usage trends

# AI Chat Streaming
POST /api/v1/analytics/ai-insights/chat/stream/     # SSE streaming chat endpoint
POST /api/v1/analytics/ai-insights/chat/quick/      # Non-streaming quick query

# RAG Document Management
GET  /api/v1/analytics/rag/documents/               # List RAG documents
POST /api/v1/analytics/rag/documents/create/        # Create document
DELETE /api/v1/analytics/rag/documents/<id>/delete/ # Delete document
POST /api/v1/analytics/rag/search/                  # Vector similarity search
POST /api/v1/analytics/rag/ingest/suppliers/        # Ingest supplier profiles
POST /api/v1/analytics/rag/ingest/insights/         # Ingest historical insights
POST /api/v1/analytics/rag/refresh/                 # Refresh all embeddings
GET  /api/v1/analytics/rag/stats/                   # RAG statistics
```

#### New Frontend Components

- **`AIInsightsChat.tsx`** - Conversational AI interface with streaming responses
- **`LLMUsageDashboard.tsx`** - Usage/cost monitoring with charts and metrics

#### New Frontend Hooks

```typescript
// Chat Streaming
useAIChatStream()              // SSE streaming with message state management
useAIQuickQuery()              // Non-streaming quick queries

// LLM Usage Tracking
useLLMUsageSummary(days)       // Usage summary data
useLLMUsageDaily(days)         // Daily usage trends

// Helper Functions
formatCost(cost)               // Format currency display
formatTokenCount(count)        // Format with K/M suffix
getRequestTypeLabel(type)      // Display labels for request types
getRequestTypeColor(type)      // Badge colors for request types
getProviderLabel(provider)     // Display labels for LLM providers
```

#### Celery Beat Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `batch_generate_insights` | 2:00 AM daily | Generate insights for all organizations |
| `batch_enhance_insights` | 2:30 AM daily | AI-enhance insights for orgs with API keys |
| `cleanup_semantic_cache` | 3:00 AM daily | Remove expired/orphaned cache entries |
| `cleanup_llm_request_logs` | 3:30 AM daily | Archive logs older than 30 days |
| `refresh_rag_documents` | 4:00 AM Sundays | Re-embed supplier profiles and insights |

#### AI Insights Page - Four Tab UI

- `/ai-insights` - Main AI Insights page with four tabs:
  - **Insights Tab**: View insights by category (Cost, Risk, Anomaly, Consolidation)
  - **ROI Tracking Tab**: Effectiveness dashboard + Action History
  - **AI Chat Tab**: Conversational AI with streaming responses
  - **Usage Tab**: LLM usage/cost dashboard with charts

#### Cost Optimization Results

| Optimization | Savings |
|--------------|---------|
| Prompt caching | 90% on cached system prompts |
| Semantic caching | 73% fewer LLM calls |
| Tiered model selection | 50% using Haiku for simple queries |
| Batch API (overnight) | 50% discount on batch jobs |

---

## Previous Updates (v2.8)

### Documentation & Presentation Materials

Added comprehensive senior management introduction materials in the `docs/` folder:

#### Generated Files
- **`docs/Management_Introduction.md`** - Full markdown documentation covering all 20 platform modules
- **`docs/generate_pdf.py`** - Python script to generate professional PDF (ReportLab)
- **`docs/generate_pptx.py`** - Python script to generate 31-slide PowerPoint deck (python-pptx)
- **`docs/screenshots/`** - 21 full-page screenshots of all application pages

#### Screenshots Captured
| Module | Files |
|--------|-------|
| **Core Dashboard** | `01_overview.png`, `02_categories.png`, `03_suppliers.png` |
| **Spend Analytics** | `04_pareto.png`, `05_stratification.png`, `15_seasonality.png`, `16_yoy.png`, `17_tail_spend.png` |
| **AI & Predictive** | `06_ai_insights.png`, `18_predictive.png` |
| **Risk & Compliance** | `19_contracts.png`, `20_maverick.png` |
| **P2P Analytics** | `08_p2p_cycle.png`, `09_matching.png`, `10_invoice_aging.png`, `11_requisitions.png`, `12_purchase_orders.png`, `13_supplier_payments.png` |
| **Reporting & Admin** | `07_reports.png`, `14_settings.png` |

#### Generate Documents
```bash
# Generate PDF
cd docs
pip install reportlab
python generate_pdf.py
# Output: Versatex_Analytics_Management_Introduction.pdf

# Generate PowerPoint
pip install python-pptx
python generate_pptx.py
# Output: Versatex_Analytics_Management_Presentation.pptx
```

---

## Previous Updates (v2.7)

### Production Hardening

This release focuses on production readiness with comprehensive security hardening:

#### New Files
- `frontend/nginx/nginx.conf` - Standalone Nginx config with CSP and security headers
- `frontend/.env.production.example` - Frontend production environment template

#### Security Headers Added
- **Content-Security-Policy (CSP)**: Prevents XSS by restricting resource loading
- **Permissions-Policy**: Disables geolocation, microphone, camera, payment, usb
- **Referrer-Policy**: Controls referrer information in requests
- **X-Frame-Options, X-Content-Type-Options, X-XSS-Protection**: Standard protections

#### Docker Improvements
- Nginx config mounted as volume in production for easy updates
- Added `/var/run` tmpfs mount for nginx pid file
- Documentation for production deployment workflow

#### Test Fixes
- Fixed 65 TypeScript mock type errors in frontend tests
- Updated TanStack Query v5 mock patterns with `as unknown as ReturnType<typeof useHook>`
- Created `createPermissionMock` helper for PermissionContext testing
- All 866 frontend tests passing with 0 TypeScript errors

---

## Previous Updates (v2.6)

### Multi-Organization User Support

Users can now belong to multiple organizations with different roles per organization. This enables consultants, auditors, and cross-functional users to access data across multiple organizations without needing separate accounts.

#### Architecture

| Model | Purpose |
|-------|---------|
| `UserProfile.organization` | User's primary/default organization (legacy, kept for backwards compatibility) |
| `UserOrganizationMembership` | Many-to-many relationship with per-org roles |

**Automatic Sync:** Django signals keep `UserProfile` and `UserOrganizationMembership` in sync:
- Changing `UserProfile.organization` creates/updates a primary membership
- Setting a membership as `is_primary=True` updates `UserProfile.organization`

#### User Types

| Type | Description | Organization Switcher |
|------|-------------|----------------------|
| **Single-org user** | Has one membership | Hidden |
| **Multi-org user** | Has 2+ memberships | Shows with role badges |
| **Superuser** | Django `is_superuser=True` | Shows all orgs with "super" badge |

#### Backend Models

```python
# UserOrganizationMembership fields
user = ForeignKey(User)           # The user
organization = ForeignKey(Org)    # The organization
role = CharField                  # 'admin', 'manager', or 'viewer'
is_primary = BooleanField         # User's default org (only one per user)
is_active = BooleanField          # Soft delete support
invited_by = ForeignKey(User)     # Who invited this user
```

#### API Endpoints

```
GET  /api/v1/auth/user/organizations/           # List user's memberships
POST /api/v1/auth/user/organizations/<id>/switch/  # Switch active org
GET  /api/v1/auth/memberships/                  # Admin: list all memberships
POST /api/v1/auth/memberships/                  # Admin: create membership
```

#### Frontend Components

- **`OrganizationContext`** (`contexts/OrganizationContext.tsx`): Manages active org state, provides `switchOrganization()`, `getRoleInOrg()`, `canSwitch`, `isMultiOrgUser`
- **`OrganizationSwitcher`** (`components/OrganizationSwitcher.tsx`): Dropdown showing orgs with role badges, primary indicator, and reset option

#### Frontend Hooks

```typescript
// From OrganizationContext
const {
  activeOrganization,    // Currently selected org
  userOrganization,      // User's primary org
  organizations,         // All orgs user can access
  activeRole,            // Role in active org
  canSwitch,             // Whether switcher should show
  isMultiOrgUser,        // Has 2+ memberships
  isViewingOtherOrg,     // Viewing non-primary org
  switchOrganization,    // (orgId) => void
  resetToDefault,        // () => void - back to primary
  getRoleInOrg,          // (orgId) => UserRole | null
} = useOrganization();
```

#### Django Admin

- **User admin**: Inline for memberships (see all orgs user belongs to)
- **User Organization Memberships**: Standalone admin with list editing
- **User Profile**: Shows membership count column

#### Adding Users to Organizations

**Via Django Admin:**
1. Go to "User organization memberships"
2. Click "Add" and select user + organization + role
3. Check "Is primary" if this should be their default org

**Via API:**
```bash
POST /api/v1/auth/memberships/
{
  "user": 1,
  "organization": 2,
  "role": "viewer",
  "is_primary": false
}
```

**Via Shell:**
```python
from apps.authentication.models import UserOrganizationMembership
UserOrganizationMembership.objects.create(
    user=user,
    organization=org,
    role='manager',
    is_primary=False
)
```

### AI Insights ROI Tracking

Track actions taken on AI-generated insights and measure their real-world effectiveness.

#### Features

| Feature | Description |
|---------|-------------|
| **Take Action Dropdown** | Record actions on insights: Implemented, Investigating, Deferred, Partially Implemented, Dismissed |
| **ROI Tracking Tab** | Dashboard showing effectiveness metrics, savings comparison, action/outcome breakdown |
| **Action History** | Paginated list of all feedback entries with filters by type, action, and outcome |
| **Outcome Updates** | Record actual results: Success, Partial Success, No Change, Failed |
| **Delete Feedback** | Remove erroneous entries (owner or admin only) |

#### AI Insights API Endpoints

```
# Core AI Insights
GET  /api/v1/analytics/ai-insights/                    # All insights with optional AI enhancement
GET  /api/v1/analytics/ai-insights/cost/               # Cost optimization insights
GET  /api/v1/analytics/ai-insights/risk/               # Supplier risk insights
GET  /api/v1/analytics/ai-insights/anomalies/          # Anomaly detection insights

# Async AI Enhancement
POST /api/v1/analytics/ai-insights/enhance/request/    # Request background AI enhancement
GET  /api/v1/analytics/ai-insights/enhance/status/     # Poll enhancement status

# Deep Analysis
POST /api/v1/analytics/ai-insights/deep-analysis/request/           # Request deep analysis for an insight
GET  /api/v1/analytics/ai-insights/deep-analysis/status/<insight_id>/ # Poll deep analysis status

# Insight Feedback (ROI Tracking)
POST   /api/v1/analytics/ai-insights/feedback/                    # Record action on an insight
GET    /api/v1/analytics/ai-insights/feedback/list/               # List feedback entries (paginated)
GET    /api/v1/analytics/ai-insights/feedback/effectiveness/      # Get ROI metrics
PATCH  /api/v1/analytics/ai-insights/feedback/<uuid:id>/          # Update outcome
DELETE /api/v1/analytics/ai-insights/feedback/<uuid:id>/delete/   # Delete feedback entry

# Metrics & Monitoring
GET  /api/v1/analytics/ai-insights/metrics/            # Internal metrics
GET  /api/v1/analytics/ai-insights/metrics/prometheus/ # Prometheus format
POST /api/v1/analytics/ai-insights/cache/invalidate/   # Invalidate AI cache

# LLM Usage & Cost Tracking
GET  /api/v1/analytics/ai-insights/usage/              # Usage summary (requests, cost, cache rate)
GET  /api/v1/analytics/ai-insights/usage/daily/        # Daily usage trends

# AI Chat Streaming
POST /api/v1/analytics/ai-insights/chat/stream/        # SSE streaming chat
POST /api/v1/analytics/ai-insights/chat/quick/         # Non-streaming query

# RAG Document Management
GET  /api/v1/analytics/rag/documents/                  # List documents
POST /api/v1/analytics/rag/search/                     # Vector similarity search
POST /api/v1/analytics/rag/ingest/suppliers/           # Ingest supplier profiles
GET  /api/v1/analytics/rag/stats/                      # RAG statistics
```

#### Frontend Hooks (`useAIInsights.ts`)

```typescript
// Core Insights
useAIInsights()                    // Fetch all AI insights
useRefreshAIInsights()             // Force refresh (bypass cache)
useAIInsightsCost()                // Cost optimization only
useAIInsightsRisk()                // Risk insights only
useAIInsightsAnomalies(sensitivity) // Anomaly detection

// Async Enhancement
useRequestAsyncEnhancement()       // Trigger background AI enhancement
useAsyncEnhancementStatus()        // Poll status with auto-refetch

// Deep Analysis
useRequestDeepAnalysis()           // Request deep analysis for an insight
useDeepAnalysisStatus(insightId)   // Poll status with auto-refetch

// Feedback (ROI Tracking)
useRecordInsightFeedback()         // Record action on insight
useInsightFeedbackList(params)     // List feedback with filters
useInsightEffectiveness()          // Get ROI metrics
useUpdateInsightOutcome()          // Update outcome for feedback
useDeleteInsightFeedback()         // Delete feedback entry

// Chat Streaming (v2.9)
useAIChatStream()                  // SSE streaming with message state
useAIQuickQuery()                  // Non-streaming quick queries

// LLM Usage Tracking (v2.9)
useLLMUsageSummary(days)           // Usage summary data
useLLMUsageDaily(days)             // Daily usage trends
formatCost(cost)                   // Format currency display
formatTokenCount(count)            // Format with K/M suffix
getRequestTypeLabel(type)          // Display labels for request types
getProviderLabel(provider)         // Display labels for LLM providers

// Helper Functions
getActionLabel(action)             // Display label for action
getActionColor(action)             // Badge color for action
getOutcomeLabel(outcome)           // Display label for outcome
getOutcomeColor(outcome)           // Badge color for outcome
```

#### Frontend Pages

- `/ai-insights` - Main AI Insights page with four tabs:
  - **Insights Tab**: View insights by category (Cost, Risk, Anomaly, Consolidation) with Take Action dropdown
  - **ROI Tracking Tab**: Effectiveness dashboard + Action History with Update/Delete actions
  - **AI Chat Tab**: Conversational AI interface with streaming responses and suggested prompts
  - **Usage Tab**: LLM usage/cost dashboard with request metrics, cache efficiency, and trend charts

#### Permission Model

| Action | Who Can Perform |
|--------|-----------------|
| View insights | All authenticated users |
| Record feedback | All authenticated users |
| Update outcome | All authenticated users |
| Delete feedback | Owner (creator) or Admin |

---

## Previous Updates (v2.5)

### P2P (Procure-to-Pay) Analytics Module

Complete procure-to-pay analytics suite tracking the full document lifecycle: PR → PO → GR → Invoice → Payment.

#### P2P Models (in `apps/procurement/models.py`)
- **PurchaseRequisition**: Internal purchase requests with approval workflow
- **PurchaseOrder**: Orders sent to suppliers with contract backing
- **GoodsReceipt**: Receipt confirmation for ordered goods
- **Invoice**: Supplier invoices with 3-way matching support

#### P2P Analytics Features
| Feature | Description |
|---------|-------------|
| **Cycle Time Analysis** | Stage-by-stage timing (PR→PO→GR→Invoice→Payment) with bottleneck detection |
| **3-Way Matching** | PO vs GR vs Invoice matching with exception management |
| **Invoice Aging** | AP aging buckets (Current, 31-60, 61-90, 90+ days) with DPO trends |
| **Requisition Tracking** | PR volume, approval rates, rejection analysis by department |
| **PO Analytics** | Contract coverage, maverick spend, amendment analysis |
| **Supplier Payments** | Payment performance scorecards with risk levels |

#### P2P API Endpoints
```
# P2P Cycle Time
GET /api/v1/analytics/p2p/cycle-overview/       # Stage timings and bottlenecks
GET /api/v1/analytics/p2p/cycle-by-category/    # Cycle times by category
GET /api/v1/analytics/p2p/cycle-by-supplier/    # Cycle times by supplier
GET /api/v1/analytics/p2p/cycle-trends/         # Monthly trend data
GET /api/v1/analytics/p2p/bottlenecks/          # Bottleneck analysis
GET /api/v1/analytics/p2p/process-funnel/       # PR→PO→GR→Invoice funnel
GET /api/v1/analytics/p2p/stage-drilldown/<stage>/  # Slowest docs per stage

# 3-Way Matching
GET /api/v1/analytics/matching/overview/        # Match rates and exceptions
GET /api/v1/analytics/matching/exceptions/      # List exceptions
GET /api/v1/analytics/matching/exceptions-by-type/    # Group by exception type
GET /api/v1/analytics/matching/exceptions-by-supplier/ # Group by supplier
GET /api/v1/analytics/matching/price-variance/  # Price variance details
GET /api/v1/analytics/matching/quantity-variance/ # Quantity variance details
GET /api/v1/analytics/matching/invoice/<id>/    # Invoice match detail
POST /api/v1/analytics/matching/invoice/<id>/resolve/  # Resolve exception
POST /api/v1/analytics/matching/exceptions/bulk-resolve/  # Bulk resolve

# Invoice Aging
GET /api/v1/analytics/aging/overview/           # AP totals, DPO, aging buckets
GET /api/v1/analytics/aging/by-supplier/        # Aging by supplier
GET /api/v1/analytics/aging/payment-terms-compliance/  # Payment terms analysis
GET /api/v1/analytics/aging/dpo-trends/         # DPO over time
GET /api/v1/analytics/aging/cash-forecast/      # Cash flow forecast

# Purchase Requisitions
GET /api/v1/analytics/requisitions/overview/    # PR metrics
GET /api/v1/analytics/requisitions/approval-analysis/  # Approval times
GET /api/v1/analytics/requisitions/by-department/  # By department
GET /api/v1/analytics/requisitions/pending/     # Pending approvals
GET /api/v1/analytics/requisitions/<id>/        # PR detail

# Purchase Orders
GET /api/v1/analytics/purchase-orders/overview/  # PO metrics
GET /api/v1/analytics/purchase-orders/leakage/   # Maverick spend
GET /api/v1/analytics/purchase-orders/amendments/ # Amendment analysis
GET /api/v1/analytics/purchase-orders/by-supplier/ # By supplier
GET /api/v1/analytics/purchase-orders/<id>/      # PO detail

# Supplier Payments
GET /api/v1/analytics/supplier-payments/overview/  # Payment metrics
GET /api/v1/analytics/supplier-payments/scorecard/ # Supplier scores
GET /api/v1/analytics/supplier-payments/<id>/      # Supplier detail
GET /api/v1/analytics/supplier-payments/<id>/history/ # Payment history
```

#### P2P Frontend Pages
- `/p2p-cycle` - Cycle time analysis dashboard
- `/matching` - 3-way matching with exception resolution
- `/invoice-aging` - AP aging analysis
- `/requisitions` - Purchase requisition tracking
- `/purchase-orders` - PO analytics
- `/supplier-payments` - Supplier payment performance

#### P2P Frontend Hooks (`useP2PAnalytics.ts`)
- Cycle: `useP2PCycleOverview()`, `useP2PCycleByCategory()`, `useP2PCycleBySupplier()`, `useP2PCycleTrends()`, `useP2PBottlenecks()`, `useP2PProcessFunnel()`, `useP2PStageDrilldown()`
- Matching: `useMatchingOverview()`, `useMatchingExceptions()`, `useExceptionsByType()`, `useExceptionsBySupplier()`, `usePriceVarianceAnalysis()`, `useQuantityVarianceAnalysis()`, `useInvoiceMatchDetail()`, `useResolveException()`, `useBulkResolveExceptions()`
- Aging: `useAgingOverview()`, `useAgingBySupplier()`, `usePaymentTermsCompliance()`, `useDPOTrends()`, `useCashFlowForecast()`
- PRs: `usePROverview()`, `usePRApprovalAnalysis()`, `usePRByDepartment()`, `usePRPending()`, `usePRDetail()`
- POs: `usePOOverview()`, `usePOLeakage()`, `usePOAmendments()`, `usePOBySupplier()`, `usePODetail()`
- Payments: `useSupplierPaymentsOverview()`, `useSupplierPaymentsScorecard()`, `useSupplierPaymentDetail()`, `useSupplierPaymentHistory()`

#### P2P Data Import
**Via Django Admin:** Each P2P model has "Import CSV" and "Download Template" buttons
- Superusers see organization dropdown to import data into any organization
- Regular users import into their profile's organization automatically

**Via Management Command:**
```bash
docker-compose exec backend python manage.py import_p2p_data \
  --org-slug <slug> --type <pr|po|gr|invoice> --file <path.csv> \
  [--skip-errors] [--dry-run]
```

#### P2P Reports (in Reports Module)
Three new P2P-specific report generators integrated into the Reports page:

| Report Type | Description | Key Metrics |
|-------------|-------------|-------------|
| **PR Status Report** | Purchase requisition workflow analysis | Total PRs, conversion rate, rejection rate, avg approval days, department breakdown |
| **PO Compliance Report** | Contract coverage and maverick analysis | Compliance score (A-F grade), contract coverage %, maverick rate, amendment patterns |
| **AP Aging Report** | Accounts payable aging analysis | Aging buckets, DPO trends, supplier aging, cash flow forecast, risk assessment |

P2P reports appear in the "P2P Analytics" category on the Reports page with teal/cyan theme.

---

## Previous Updates (v2.4)

### Reports UI Enhancements
- **Categorized Report Generation**: Reports organized into categories (Executive & Overview, Supplier Intelligence, Trends & Patterns, Optimization & Compliance)
- **Report Badges**: Visual indicators for New, Popular, and Recommended reports
- **Themed Report Cards**: Each report type has unique gradient colors, icons, and hover effects
- **History Tab Makeover**: Gradient header, themed report icons, format badges (PDF/Excel/CSV), hover effects
- **Schedules Tab Makeover**: Indigo/purple theme, frequency color badges (daily/weekly/monthly), improved action buttons

### Organization Branding for PDF Reports
- **Logo Support**: Upload organization logo (recommended: 200x60px PNG) via Django Admin
- **Custom Colors**: Set primary and secondary brand colors (hex format) applied to PDF headers
- **Footer Customization**: Add custom footer text (e.g., confidentiality notices)
- **Website URL**: Display organization website in PDF footer
- Branding fields on Organization model: `logo`, `primary_color`, `secondary_color`, `report_footer`, `website`
- Access branding via `organization.get_branding()` method

---

## Previous Updates (v2.3)

### Reports Module
- **Report Generation**: Generate procurement reports in PDF, Excel (XLSX), or CSV formats
- **11 Report Types**: Executive Summary, Spend Analysis, Supplier Performance, Pareto Analysis, Contract Compliance, Savings Opportunities, Spend Stratification, Seasonality & Trends, Year-over-Year Analysis, Tail Spend Analysis
- **Async Generation**: Large reports generated via Celery with real-time status polling
- **Report Scheduling**: Create recurring reports (daily, weekly, bi-weekly, monthly, quarterly)
- **Multi-tenant**: All reports scoped by organization
- **Report Preview**: Preview report data before generating the full report
- **Advanced Filtering**: Filter reports by suppliers, categories, and amount ranges
- **Professional PDF Styling**: Executive headers with org branding, KPI cards with auto-sizing, smart table column widths, page numbers

### New Report Types (v2.3)
| Report Type | Description | Key Metrics |
|-------------|-------------|-------------|
| **Spend Stratification** | Kraljic matrix analysis | Segments (Strategic/Leverage/Routine/Tactical), spend bands, risk assessment |
| **Seasonality & Trends** | Monthly spending patterns | Seasonal indices, peak/trough analysis, savings opportunities |
| **Year-over-Year** | YoY comparison | Top gainers/decliners, variance analysis, monthly comparison |
| **Tail Spend** | Vendor fragmentation analysis | Tail vendor count, consolidation opportunities, action plans |

Report-specific parameters:
- **Seasonality**: `use_fiscal_year` (boolean, default: true) - Use fiscal year (Jul-Jun) vs calendar year
- **Year-over-Year**: `year1`, `year2` (integers), `use_fiscal_year` (boolean)
- **Tail Spend**: `threshold` (integer, default: 50000) - Dollar amount threshold for tail classification

### Reports API Endpoints
```
GET    /api/v1/reports/templates/                    # List available report templates
GET    /api/v1/reports/templates/<id>/               # Get template details
POST   /api/v1/reports/generate/                     # Generate a report (sync or async)
POST   /api/v1/reports/preview/                      # Generate lightweight preview data
GET    /api/v1/reports/                              # List generated reports
GET    /api/v1/reports/<id>/                         # Get report details
GET    /api/v1/reports/<id>/status/                  # Poll generation status
GET    /api/v1/reports/<id>/download/?output_format= # Download report (pdf/xlsx/csv)
DELETE /api/v1/reports/<id>/                         # Delete report
POST   /api/v1/reports/<id>/share/                   # Share report with users
GET    /api/v1/reports/schedules/                    # List scheduled reports
POST   /api/v1/reports/schedules/                    # Create schedule
GET    /api/v1/reports/schedules/<id>/               # Get schedule details
PUT    /api/v1/reports/schedules/<id>/               # Update schedule
DELETE /api/v1/reports/schedules/<id>/               # Delete schedule
POST   /api/v1/reports/schedules/<id>/run-now/       # Trigger immediate generation
```

### Report Generation Filters
Reports support advanced filtering via the `filters` parameter:
```json
{
  "supplier_ids": [1, 2, 3],      // Filter by specific suppliers
  "category_ids": [1, 2],          // Filter by specific categories
  "min_amount": 1000.00,           // Minimum transaction amount
  "max_amount": 50000.00           // Maximum transaction amount
}
```
Date filtering is handled via `period_start` and `period_end` fields.

### Reports Frontend Hooks
- `useReportTemplates()` - List available report templates
- `useReportHistory()` - List generated reports with pagination
- `useReportStatus(id)` - Poll generation status (2s interval while generating)
- `useGenerateReport()` - Mutation to generate report
- `useReportPreview()` - Mutation to generate lightweight preview data
- `useDownloadReport()` - Mutation to download report file
- `useReportSchedules()` - List scheduled reports
- `useCreateSchedule()`, `useUpdateSchedule()`, `useDeleteSchedule()` - Schedule CRUD
- `useRunScheduleNow()` - Trigger immediate schedule execution

### Reports Page Features
- **Generate Tab**: Click report type cards to configure and generate
- **Preview Button**: Preview report data before full generation
- **Advanced Filters**: Filter by suppliers, categories, and amount range (collapsible UI)
- **Preview Dialog**: Shows key metrics, top categories/suppliers before generating
- **History Tab**: View past reports with status badges, download/delete actions
- **Schedules Tab**: Create/edit/delete recurring report schedules

---

## Previous Updates (v2.2)

### Dashboard Page Enhancements
- **Backend-Powered Analytics**: All dashboard pages now use pre-computed backend data instead of client-side aggregation
- **Drill-Down Modals**: Click chart segments/rows to see detailed breakdowns:
  - Pareto Analysis: Supplier drill-down with category breakdown
  - Spend Stratification: Segment and band drill-downs
  - Seasonality: Category drill-down with supplier details + heatmap visualization
  - Year-over-Year: Category and supplier drill-downs with monthly breakdown
  - Tail Spend: Category and vendor drill-downs with adjustable threshold slider
- **Organization Context**: All query keys include org ID for proper cache isolation when switching organizations (superuser feature)
- **AI Insights**: Savings visualization donut chart, sort dropdown (severity/savings/confidence)
- **Predictive Analytics**: Model accuracy tooltips explaining MAPE/R² metrics in plain English
- **Contracts**: Contract detail modal with utilization progress, dates, category breakdown, monthly spend
- **Maverick Spend**: Batch violation resolution (checkbox selection + bulk resolve with single notes modal)

### New Backend Endpoints
```
/api/v1/analytics/pareto/detailed/              # Pareto with supplier drill-down
/api/v1/analytics/stratification/detailed/      # Stratification with segment/band details
/api/v1/analytics/seasonality/detailed/         # Seasonality with category drill-down
/api/v1/analytics/year-over-year/detailed/      # YoY with category/supplier drill-down
/api/v1/analytics/tail-spend/detailed/          # Tail spend with threshold parameter
/api/v1/analytics/contracts/overview/           # Contract portfolio overview
/api/v1/analytics/contracts/<id>/               # Contract detail
/api/v1/analytics/compliance/overview/          # Compliance statistics
/api/v1/analytics/compliance/violations/        # Policy violations list
```

### Frontend Hooks
- `useDetailedPareto()`, `useParetoDrilldown()` - Pareto analysis
- `useDetailedStratification()`, `useStratificationDrilldown()` - Spend stratification
- `useDetailedSeasonality()`, `useSeasonalityCategoryDrilldown()` - Seasonality
- `useDetailedYearOverYear()`, `useYoYCategoryDrilldown()`, `useYoYSupplierDrilldown()` - YoY
- `useDetailedTailSpend()`, `useTailSpendCategoryDrilldown()`, `useTailSpendVendorDrilldown()` - Tail spend
- `useContractOverview()`, `useContracts()`, `useContractDetail()` - Contracts
- `useComplianceOverview()`, `usePolicyViolations()`, `useResolveViolation()` - Compliance

## Previous Updates (v2.0)

### Dashboard Enhancements
- **Data Refresh Button**: Manual refresh in header to pull latest data after admin uploads
- **Export Functionality**: CSV export with role-based permissions (CanExport gate)
- **Date Range Presets**: Quick presets (Last 7/30/90 days, This Year, Last Year)
- **Skeleton Loaders**: Polished loading states for cards and charts
- **Dark Mode Improvements**: ECharts fully respects dark/light theme
- **Mobile Responsiveness**: Bottom sheet filter pane on mobile devices
- **Saved Filter Presets**: Save/load filter combinations (localStorage)
- **Data Polling**: 60-second polling for new data notifications
- **User Preferences Sync**: Settings sync to backend UserProfile model
- **Chunk Optimization**: Vite manualChunks for better code splitting

### Architecture
- **Admin Panel Only**: Data uploads handled via Django Admin (no frontend upload)
- **RBAC System**: Role-based access control with PermissionGate components
- **HTTP-only Cookies**: JWT tokens stored in secure cookies for XSS protection
