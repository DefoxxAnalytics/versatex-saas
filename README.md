# Versatex Analytics 2.10

[![CI](https://github.com/DefoxxAnalytics/versatex-saas/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/DefoxxAnalytics/versatex-saas/actions/workflows/ci.yml)
[![Production Ready](https://img.shields.io/badge/Production-Ready-brightgreen.svg)](docs/SHIPPING_READINESS.md)
[![Security](https://img.shields.io/badge/Security-8.5%2F10-green.svg)](docs/SHIPPING_READINESS.md)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-311/)
[![Django 5.0](https://img.shields.io/badge/Django-5.0-green.svg)](https://docs.djangoproject.com/en/5.0/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178c6.svg)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.0-38bdf8.svg)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](https://www.docker.com/)
[![Railway](https://img.shields.io/badge/Railway-Deployable-0B0D0E.svg)](https://railway.app/)

> Enterprise-grade procurement analytics platform with organization-based multi-tenancy, real-time insights, and comprehensive spend analysis.

---

## Overview

Versatex Analytics is a full-stack procurement analytics dashboard designed for organizations to gain actionable insights from their spending data. Built with modern technologies and security best practices, it provides powerful analytics capabilities while maintaining data isolation across multiple tenants.

## Architecture

| Layer | Technology |
|-------|------------|
| **Backend** | Django 5.0 + Django REST Framework + PostgreSQL |
| **Frontend** | React 18 + TypeScript + Tailwind CSS 4 + Vite |
| **Authentication** | JWT tokens with role-based access control |
| **Database** | PostgreSQL with pgvector for vector search |
| **AI/LLM** | Claude/OpenAI with semantic caching + RAG |
| **Task Queue** | Celery + Redis for background jobs |
| **Deployment** | Docker + Docker Compose / Railway |

## Features

### Authentication & Authorization
- User registration and login with JWT token authentication
- Organization-based multi-tenancy with complete data isolation
- **Multi-organization user support** - Users can belong to multiple organizations with different roles per org
- Role-based permissions (Admin, Manager, Viewer) per organization
- Audit logging for compliance and security
- Custom branded admin panel with Versatex theming

### Data Management
- CSV upload with intelligent duplicate detection
- Bulk operations (delete, export)
- Supplier and category management
- Transaction CRUD operations with validation
- Upload history tracking with batch management

### Analytics Suite
| Analysis Type | Description |
|--------------|-------------|
| **Overview** | Key metrics and statistics at a glance |
| **Spend by Category/Supplier** | Breakdown of spending patterns |
| **Monthly Trends** | Time-series analysis of procurement |
| **Pareto Analysis** | 80/20 rule identification |
| **Tail Spend** | Low-value transaction identification |
| **Spend Stratification** | Kraljic Matrix classification |
| **Seasonality** | Pattern detection across periods |
| **Year-over-Year** | Comparative analysis |
| **Consolidation** | Supplier optimization opportunities |
| **AI Insights** | AI-powered recommendations with ROI tracking |
| **Predictive Analytics** | Spending forecasts and trend predictions |
| **Contract Analytics** | Contract utilization, renewals, and compliance |
| **Compliance/Maverick Spend** | Policy violations and spending compliance |

### AI Insights Module (v2.9)
| Feature | Description |
|---------|-------------|
| **Cost Optimization** | Price variance detection across suppliers |
| **Supplier Risk** | Concentration risk and dependency analysis |
| **Anomaly Detection** | Z-score based statistical outlier detection |
| **Consolidation** | Multi-supplier category recommendations |
| **External AI Enhancement** | Claude/OpenAI integration for deeper analysis |
| **Deep Analysis** | On-demand detailed analysis per insight |
| **ROI Tracking** | Track actions taken on insights and actual savings realized |
| **Effectiveness Dashboard** | Metrics on insight implementation success |
| **Action History** | Full history of recorded actions with CRUD support |
| **AI Chat (Streaming)** | Conversational AI interface with real-time SSE streaming |
| **LLM Usage Dashboard** | Cost tracking, cache efficiency metrics, and usage trends |
| **Semantic Caching** | pgvector-powered similarity search (90% threshold) for cost reduction |
| **RAG Document Intelligence** | Vector search for supplier profiles and historical insights |
| **Batch Processing** | Overnight insight generation via Celery Beat |
| **Hallucination Prevention** | Validation layer for monetary values, suppliers, and dates |

### Reports Module
| Feature | Description |
|---------|-------------|
| **Report Generation** | Generate reports in PDF, Excel (XLSX), or CSV formats |
| **13 Report Types** | Executive Summary, Spend Analysis, Supplier Performance, Pareto Analysis, Contract Compliance, Savings Opportunities, Stratification, Seasonality, Year-over-Year, Tail Spend, plus 3 P2P reports |
| **Async Generation** | Large reports generated via Celery with real-time status polling |
| **Report Preview** | Preview report data before generating the full report |
| **Advanced Filtering** | Filter by suppliers, categories, and amount ranges |
| **Report Scheduling** | Create recurring reports (daily, weekly, bi-weekly, monthly, quarterly) |
| **Professional PDF** | Executive headers, KPI cards, smart table layouts, page numbers |

### P2P Analytics Module
| Feature | Description |
|---------|-------------|
| **Data Models** | Purchase Requisitions (PR), Purchase Orders (PO), Goods Receipts (GR), Invoices |
| **P2P Cycle Dashboard** | End-to-end process visibility with cycle time metrics |
| **Three-Way Matching** | Automated PO-GR-Invoice matching with exception management |
| **Invoice Aging** | Aging buckets, DPO trends, payment performance analytics |
| **Requisitions Analysis** | PR status tracking, approval workflows, department breakdowns |
| **Purchase Orders** | PO compliance, contract coverage, maverick spend detection |
| **Supplier Payments** | Payment terms compliance, cash flow forecasting |
| **P2P Reports** | PR Status Report, PO Compliance Report, AP Aging Report |
| **Admin Import** | CSV import for all P2P documents with superuser org selection |

### Security Features
- Argon2 password hashing
- JWT token authentication with HTTP-only cookies
- CORS protection with strict origin validation
- SQL injection and XSS protection
- CSRF protection with SameSite cookies
- Rate limiting (login: 5/min, uploads: 10/hr, API: 1000/hr)
- HTTPS enforcement with HSTS (1 year)
- UUID-based resource identifiers (IDOR protection)
- Failed login tracking with IP lockout
- Content Security Policy (CSP) headers
- Permissions-Policy (disables geolocation, microphone, camera)
- Container security (non-root user, read-only filesystem, no-new-privileges)

## Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) Python 3.11+ and Node.js 22+ for local development

### 1. Clone and Setup

```bash
git clone https://github.com/DefoxxAnalytics/versatex-saas.git
cd versatex-saas

# Copy environment variables
cp .env.example .env

# Edit .env and set your configuration
nano .env
```

### 2. Start with Docker

```bash
# Build and start all services
docker-compose up -d --build

# Check logs
docker-compose logs -f

# Services available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8001/api
# - Django Admin: http://localhost:8001/admin
# - API Docs: http://localhost:8001/api/docs
```

### 3. Initialize Database

```bash
# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Create initial organization
docker-compose exec backend python manage.py shell
>>> from apps.authentication.models import Organization
>>> org = Organization.objects.create(name="My Company", slug="my-company")
>>> exit()
```

### 4. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Main application |
| Django Admin | http://localhost:8001/admin | Administration panel |
| API Docs | http://localhost:8001/api/docs | Interactive API documentation |

## API Reference

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register/` | POST | Register new user |
| `/api/v1/auth/login/` | POST | Login |
| `/api/v1/auth/logout/` | POST | Logout |
| `/api/v1/auth/token/refresh/` | POST | Refresh JWT token |
| `/api/v1/auth/user/` | GET | Get current user |
| `/api/v1/auth/change-password/` | POST | Change password |
| `/api/v1/auth/user/organizations/` | GET | List user's organization memberships |
| `/api/v1/auth/user/organizations/<id>/switch/` | POST | Switch active organization |
| `/api/v1/auth/memberships/` | GET/POST | Manage organization memberships (admin) |

### Procurement
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/procurement/suppliers/` | GET/POST | List/create suppliers |
| `/api/v1/procurement/categories/` | GET/POST | List/create categories |
| `/api/v1/procurement/transactions/` | GET/POST | List/create transactions |
| `/api/v1/procurement/transactions/upload_csv/` | POST | Upload CSV data |
| `/api/v1/procurement/transactions/bulk_delete/` | POST | Bulk delete |
| `/api/v1/procurement/transactions/export/` | GET | Export to CSV |

### Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/overview/` | GET | Overview statistics |
| `/api/v1/analytics/spend-by-category/` | GET | Spend by category |
| `/api/v1/analytics/spend-by-supplier/` | GET | Spend by supplier |
| `/api/v1/analytics/monthly-trend/` | GET | Monthly trend |
| `/api/v1/analytics/pareto/` | GET | Pareto analysis |
| `/api/v1/analytics/tail-spend/` | GET | Tail spend analysis |
| `/api/v1/analytics/stratification/` | GET | Spend stratification |
| `/api/v1/analytics/seasonality/` | GET | Seasonality analysis |
| `/api/v1/analytics/year-over-year/` | GET | Year over year |
| `/api/v1/analytics/consolidation/` | GET | Consolidation opportunities |

### AI Insights
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/ai-insights/` | GET | All AI insights combined |
| `/api/v1/analytics/ai-insights/cost/` | GET | Cost optimization insights |
| `/api/v1/analytics/ai-insights/risk/` | GET | Supplier risk insights |
| `/api/v1/analytics/ai-insights/anomalies/` | GET | Anomaly detection insights |
| `/api/v1/analytics/ai-insights/enhance/request/` | POST | Trigger async AI enhancement |
| `/api/v1/analytics/ai-insights/enhance/status/` | GET | Poll enhancement status |
| `/api/v1/analytics/ai-insights/deep-analysis/request/` | POST | Request deep analysis |
| `/api/v1/analytics/ai-insights/deep-analysis/status/<id>/` | GET | Poll deep analysis status |
| `/api/v1/analytics/ai-insights/feedback/` | POST | Record insight feedback |
| `/api/v1/analytics/ai-insights/feedback/list/` | GET | List feedback history |
| `/api/v1/analytics/ai-insights/feedback/effectiveness/` | GET | Get effectiveness metrics |
| `/api/v1/analytics/ai-insights/feedback/<id>/` | PATCH | Update outcome |
| `/api/v1/analytics/ai-insights/feedback/<id>/delete/` | DELETE | Delete feedback entry |
| `/api/v1/analytics/ai-insights/metrics/` | GET | AI insights metrics |
| `/api/v1/analytics/ai-insights/cache/invalidate/` | POST | Invalidate AI cache |
| `/api/v1/analytics/ai-insights/usage/` | GET | LLM usage summary (cost, cache rate) |
| `/api/v1/analytics/ai-insights/usage/daily/` | GET | Daily LLM usage trends |
| `/api/v1/analytics/ai-insights/chat/stream/` | POST | AI chat with SSE streaming |
| `/api/v1/analytics/ai-insights/chat/quick/` | POST | Non-streaming quick query |
| `/api/v1/analytics/rag/documents/` | GET | List RAG documents |
| `/api/v1/analytics/rag/search/` | POST | Vector similarity search |
| `/api/v1/analytics/rag/ingest/suppliers/` | POST | Ingest supplier profiles |
| `/api/v1/analytics/rag/stats/` | GET | RAG statistics |

### Predictive Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/predictions/spending/` | GET | Spending forecast |
| `/api/v1/analytics/predictions/category/<id>/` | GET | Category forecast |
| `/api/v1/analytics/predictions/supplier/<id>/` | GET | Supplier forecast |
| `/api/v1/analytics/predictions/trends/` | GET | Trend analysis |
| `/api/v1/analytics/predictions/budget/` | GET | Budget projection |

### Contracts
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/contracts/overview/` | GET | Contract portfolio overview |
| `/api/v1/analytics/contracts/` | GET | List contracts |
| `/api/v1/analytics/contracts/<id>/` | GET | Contract detail |
| `/api/v1/analytics/contracts/expiring/` | GET | Expiring contracts |
| `/api/v1/analytics/contracts/<id>/performance/` | GET | Contract performance |
| `/api/v1/analytics/contracts/savings/` | GET | Savings opportunities |

### Compliance
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/compliance/overview/` | GET | Compliance statistics |
| `/api/v1/analytics/compliance/maverick-spend/` | GET | Maverick spend analysis |
| `/api/v1/analytics/compliance/violations/` | GET | Policy violations list |
| `/api/v1/analytics/compliance/violations/<id>/resolve/` | POST | Resolve violation |

### Reports
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/reports/templates/` | GET | List available report templates |
| `/api/v1/reports/generate/` | POST | Generate a report (sync or async) |
| `/api/v1/reports/preview/` | POST | Generate lightweight preview data |
| `/api/v1/reports/` | GET | List generated reports |
| `/api/v1/reports/<id>/` | GET | Get report details |
| `/api/v1/reports/<id>/status/` | GET | Poll generation status |
| `/api/v1/reports/<id>/download/` | GET | Download report (pdf/xlsx/csv) |
| `/api/v1/reports/<id>/` | DELETE | Delete report |
| `/api/v1/reports/schedules/` | GET/POST | List/create scheduled reports |
| `/api/v1/reports/schedules/<id>/` | GET/PUT/DELETE | Schedule CRUD |
| `/api/v1/reports/schedules/<id>/run-now/` | POST | Trigger immediate generation |

### P2P Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/p2p/cycle/` | GET | P2P cycle overview with stage metrics |
| `/api/v1/analytics/p2p/matching/` | GET | Three-way matching analytics |
| `/api/v1/analytics/p2p/aging/` | GET | Invoice aging overview |
| `/api/v1/analytics/p2p/requisitions/` | GET | Purchase requisition analytics |
| `/api/v1/analytics/p2p/purchase-orders/` | GET | Purchase order analytics |
| `/api/v1/analytics/p2p/supplier-payments/` | GET | Supplier payment analytics |

## Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Frontend Development

```bash
cd frontend

# Install dependencies
pnpm install

# Run development server
pnpm dev

# Type checking
pnpm check

# Build for production
pnpm build
```

### Production Deployment

```bash
# Deploy with production Docker Compose (enhanced security)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Verify security headers
curl -I https://your-frontend-domain.com
```

Production features:
- Internal network isolation (no external DB/Redis access)
- Redis authentication required
- Read-only frontend filesystem
- Resource limits (CPU/memory caps)
- Security headers (CSP, Permissions-Policy, Referrer-Policy)
- Non-root container users

See [Production Checklist](docs/SHIPPING_READINESS.md) for complete deployment guide.

### Testing

**Backend:** 621 tests, 70% coverage
```bash
cd backend
python manage.py test
# Or with coverage
docker-compose exec backend pytest --cov=apps
```

**Frontend:** 866 tests
```bash
cd frontend
pnpm test        # Watch mode
pnpm test:run    # Single run
pnpm test:ui     # With UI
```

## Database Schema

### Core Models

| Model | Description |
|-------|-------------|
| **Organization** | Multi-tenant root with isolated data |
| **User/UserProfile** | Extended Django User with org, role |
| **UserOrganizationMembership** | Many-to-many relationship for multi-org users with per-org roles |
| **Supplier** | Vendor information |
| **Category** | Spend categories (hierarchical) |
| **Transaction** | Procurement transactions |
| **DataUpload** | Upload history tracking |
| **Report** | Generated reports with scheduling support |
| **InsightFeedback** | Track actions taken on AI insights and actual savings |
| **Contract** | Contract details with utilization tracking |
| **PolicyViolation** | Compliance violations and resolutions |
| **LLMRequestLog** | Track all LLM API calls (tokens, cost, latency, cache) |
| **SemanticCache** | pgvector embeddings for semantic similarity search |
| **EmbeddedDocument** | RAG document store with vector embeddings |

### P2P Models

| Model | Description |
|-------|-------------|
| **PurchaseRequisition** | PR with status, department, cost center, approval workflow |
| **PurchaseOrder** | PO with supplier, amounts, contract backing, amendments |
| **GoodsReceipt** | GR linked to PO with quantity received/accepted |
| **Invoice** | Invoice with matching status, payment terms, exceptions |

### User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access, user management, bulk delete, Django Admin |
| **Manager** | Upload data, manage own data |
| **Viewer** | Read-only access |

**Multi-Organization Support:** Users can have different roles in different organizations. For example, a consultant might be an Admin in one organization and a Viewer in another. The frontend organization switcher shows role badges for each organization.

## Deployment

### Railway (Recommended)

Railway provides native support for the full stack with minimal configuration.

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and initialize
railway login
railway init

# Deploy
railway up
```

**Cost Estimate:**
- Development: ~$15-20/month
- Production: ~$40-50/month

See [Railway Step-by-Step Guide](docs/deployment/RAILWAY-STEP-BY-STEP.md) for detailed instructions.

### Docker Compose (Self-Hosted)

```bash
# Production deployment
docker-compose --profile production up -d

# With custom port
FRONTEND_PORT=8080 docker-compose up -d
```

## Theme & Branding

Three built-in color schemes, togglable per user from **Settings → Theme Preferences**. Each supports both light and dark mode.

| Scheme | Description |
|--------|-------------|
| **Navy Blue & White** (default) | Modern navy chrome, blue chart series |
| **Classic (Original)** | Original white sidebar with blue accents |
| **Versatex Brand** | Official brand palette — charcoal chrome (100% / 80% / 40% black + white) with signature yellow `#FDC00F` (PMS 1235 C) as accent on active states, focus rings, avatar, and chart series |

Theme preferences are persisted to the user's profile and apply across all organizations the user belongs to. See [BrandGuidelines2.png](BrandGuidelines2.png) for the brand palette reference.

## Demo Data Seeding

Two management commands populate any organization with realistic, industry-specific demo data end-to-end. Useful for standing up demos or refilling empty dashboards. Full reference in [docs/DEMO_DATA.md](docs/DEMO_DATA.md).

### Supported industry profiles

| Profile | Default Org Name | Scale |
|---------|------------------|-------|
| `healthcare` | Mercy Regional Medical Center | ~$650M spend, 603 suppliers, 15 categories (Pharma, Med/Surg, Implants, Imaging, Lab...) |
| `higher-ed` | Pacific State University | ~$1.68B spend, 541 suppliers, 16 categories (Research Lab, Library, Facilities, Athletics...) |
| `manufacturing` | Apex Manufacturing Co. | ~$785M spend, 576 suppliers, 15 categories (Raw Materials, Components, MRO, Industrial Equipment, Tooling...) |

Both ship with real industry vendor names (GE Healthcare / Philips / Stryker / Cardinal Health for healthcare; Turner Construction / Skanska / Thermo Fisher / Elsevier for higher-ed), industry-appropriate departments, payment terms, seasonality, and spending policies.

### Commands

```bash
# Healthcare: create/rename org, seed base data, then P2P layer
docker-compose exec backend python manage.py seed_industry_data --industry healthcare --org-slug uch --wipe
docker-compose exec backend python manage.py seed_demo_data --org uch --industry healthcare --wipe

# Higher Education
docker-compose exec backend python manage.py seed_industry_data --industry higher-ed --org-slug tsu --wipe
docker-compose exec backend python manage.py seed_demo_data --org tsu --industry higher-ed --wipe

# Manufacturing (Bolt & Nuts, slug `eaton`) - full reseed from the manufacturing profile
docker-compose exec backend python manage.py seed_industry_data --industry manufacturing --org-slug eaton --org-name "Bolt & Nuts Manufacturing" --wipe
docker-compose exec backend python manage.py seed_demo_data --org eaton --industry manufacturing --wipe
```

Both commands are idempotent via `--wipe` and deterministic via `--seed` (default 42). Profiles live in [backend/apps/procurement/management/commands/_industry_profiles.py](backend/apps/procurement/management/commands/_industry_profiles.py) and are easy to extend.

## CSV Upload Format

### Required Columns
| Column | Description |
|--------|-------------|
| `supplier` | Supplier name |
| `category` | Category name |
| `amount` | Transaction amount |
| `date` | Transaction date (YYYY-MM-DD) |

### Optional Columns
| Column | Description |
|--------|-------------|
| `description` | Transaction description |
| `subcategory` | Subcategory |
| `location` | Location |
| `fiscal_year` | Fiscal year |
| `spend_band` | Spend band |
| `payment_method` | Payment method |
| `invoice_number` | Invoice number |

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/setup/QUICK_START_GUIDE.md) | Fast setup for development |
| [Windows Setup](docs/setup/WINDOWS-SETUP.md) | Windows-specific instructions |
| [Docker Troubleshooting](docs/setup/DOCKER-TROUBLESHOOTING.md) | Common issues and solutions |
| [Railway Deployment](docs/deployment/RAILWAY-STEP-BY-STEP.md) | Production deployment guide |
| [Shipping Readiness](docs/SHIPPING_READINESS.md) | Production checklist and security assessment |
| [Development Guide](CLAUDE.md) | Development guidelines and API documentation |
| [AI Insights Enhancement](docs/AI_INSIGHTS_ENHANCEMENT_PLAN.md) | AI Insights feature roadmap and implementation status |
| [P2P Analytics Guide](docs/P2P_USER_GUIDE.md) | P2P module user documentation |
| [Demo Data Seeding](docs/DEMO_DATA.md) | Industry-specific seed commands (Healthcare, Higher Ed, Manufacturing) |

## Troubleshooting

### Database Connection Issues
```bash
docker-compose ps db
docker-compose logs db
docker-compose restart db
```

### Backend Issues
```bash
docker-compose logs backend
docker-compose restart backend
docker-compose exec backend python manage.py migrate
```

### Frontend Issues
```bash
docker-compose logs frontend
docker-compose up -d --build frontend
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved. See [LICENSE](LICENSE) for details.

## Credits

Built with Django, React, PostgreSQL, and Docker by [Defoxx Analytics](https://github.com/DefoxxAnalytics).

---

<p align="center">
  <sub>Made with care by the Versatex team</sub>
</p>
