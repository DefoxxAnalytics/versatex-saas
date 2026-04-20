# Technical Debt Prevention Guide

**Created:** 2026-01-08
**Applies to:** Versatex Analytics v2.6+
**Purpose:** Prevent debt before it accumulates

---

## Executive Summary

This guide establishes **proactive measures** to prevent technical debt from accumulating in the Versatex Analytics codebase. Prevention is always cheaper than remediation.

**Core Principle:** Every piece of debt added intentionally must have:
1. A documented reason
2. A sunset date
3. A tracking ID in `TECHNICAL_DEBT.md`

---

## 1. Code Architecture Prevention

### 1.1 Service File Size Limits

**Problem:** Services like `AnalyticsService` grow into 2000+ line monoliths.

**Prevention:**

```yaml
# .github/workflows/ci.yml - Add to CI pipeline
- name: Check service file sizes
  run: |
    echo "Checking for oversized service files..."
    find backend/apps -name "services.py" -o -name "*_services.py" | while read file; do
      lines=$(wc -l < "$file")
      if [ "$lines" -gt 500 ]; then
        echo "ERROR: $file has $lines lines (max: 500)"
        exit 1
      elif [ "$lines" -gt 400 ]; then
        echo "WARNING: $file has $lines lines (approaching limit)"
      fi
    done
```

**Code Review Checklist:**
- [ ] Does this method belong in this service, or a new domain-specific service?
- [ ] Is the service approaching 400 lines? Time to split.
- [ ] Are there 3+ methods with similar prefixes (e.g., `get_supplier_*`)? Extract to dedicated service.

### 1.2 Domain-Driven Service Structure

**Recommended Structure:**

```
apps/analytics/services/
├── __init__.py              # Re-exports for backwards compatibility
├── base.py                  # BaseAnalyticsService with common methods
├── spend_analytics.py       # SpendAnalyticsService (spend analysis, stratification)
├── supplier_analytics.py    # SupplierAnalyticsService (drilldowns, consolidation)
├── trend_analytics.py       # TrendAnalyticsService (seasonality, YoY, monthly)
├── compliance_analytics.py  # ComplianceAnalyticsService (contracts, violations)
└── p2p_analytics.py         # P2PAnalyticsService (cycle, matching, aging)
```

**When to Create a New Service:**
- 5+ related methods exist
- Methods share a common domain concept
- Methods have shared dependencies (same models, same external APIs)

---

## 2. Performance Debt Prevention

### 2.1 Query Monitoring from Day 1

**Setup django-silk for development:**

```python
# backend/config/settings.py (development only)
if DEBUG:
    INSTALLED_APPS += ['silk']
    MIDDLEWARE += ['silk.middleware.SilkyMiddleware']
    SILKY_PYTHON_PROFILER = True
    SILKY_MAX_RECORDED_REQUESTS = 1000
    SILKY_META = True
```

```python
# backend/config/urls.py (development only)
if settings.DEBUG:
    urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
```

**Dashboard URL:** `http://localhost:8001/silk/`

### 2.2 Performance Budgets

**Endpoint Response Time Limits:**

| Endpoint Type | Max Response Time | At Row Count |
|---------------|-------------------|--------------|
| List endpoints | 200ms | 1,000 rows |
| Analytics overview | 500ms | 100,000 rows |
| Drilldown endpoints | 300ms | 10,000 rows |
| Report generation | 5s | 500,000 rows |
| CSV export | 10s | 1,000,000 rows |

**CI Performance Check:**

```yaml
# .github/workflows/ci.yml
- name: Performance budget check
  run: |
    # Start test server with seeded data
    python manage.py loaddata performance_test_data.json

    # Run k6 performance tests
    k6 run tests/performance/budget_check.js --threshold 'http_req_duration{endpoint:overview}<500'
```

### 2.3 Aggregation Query Guidelines

**Bad Pattern (will degrade at scale):**

```python
# Real-time aggregation on every request
def get_total_spend(self, organization):
    return Transaction.objects.filter(
        organization=organization
    ).aggregate(total=Sum('amount'))['total']
```

**Better Pattern (with caching):**

```python
from django.core.cache import cache

def get_total_spend(self, organization):
    cache_key = f'total_spend_{organization.id}'
    total = cache.get(cache_key)

    if total is None:
        total = Transaction.objects.filter(
            organization=organization
        ).aggregate(total=Sum('amount'))['total']
        cache.set(cache_key, total, timeout=300)  # 5 min cache

    return total
```

**Best Pattern (materialized view - for future):**

```sql
-- PostgreSQL materialized view
CREATE MATERIALIZED VIEW mv_organization_spend AS
SELECT
    organization_id,
    date_trunc('month', date) as month,
    SUM(amount) as total_spend,
    COUNT(*) as transaction_count
FROM procurement_transaction
GROUP BY organization_id, date_trunc('month', date);

-- Refresh strategy: every hour or on data upload
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_organization_spend;
```

---

## 3. API Contract Prevention

### 3.1 Automated TypeScript Generation

**Setup (one-time):**

```bash
cd frontend
pnpm add -D openapi-typescript
```

**CI Pipeline:**

```yaml
# .github/workflows/ci.yml
- name: Generate TypeScript types from OpenAPI
  run: |
    # Start backend to get schema
    cd backend && python manage.py runserver &
    sleep 5

    # Generate types
    cd frontend
    npx openapi-typescript http://localhost:8000/api/schema/ -o src/lib/api-types.generated.ts

    # Check for drift
    git diff --exit-code src/lib/api-types.generated.ts || {
      echo "ERROR: API types are out of sync!"
      echo "Run: npx openapi-typescript http://localhost:8001/api/schema/ -o src/lib/api-types.generated.ts"
      exit 1
    }
```

**Pre-commit hook:**

```bash
# .husky/pre-commit
#!/bin/sh
cd frontend
npx openapi-typescript http://localhost:8001/api/schema/ -o src/lib/api-types.generated.ts
git add src/lib/api-types.generated.ts
```

### 3.2 API Versioning Strategy

**Current:** `/api/v1/` (correct)
**Legacy:** `/api/` (deprecated)

**Rules:**
1. Breaking changes require new version (`/api/v2/`)
2. Deprecation period: 6 months minimum
3. All deprecated endpoints must log usage
4. Sunset dates must be in code comments AND `TECHNICAL_DEBT.md`

**Deprecation Middleware:**

```python
# backend/apps/core/middleware.py
import logging
from django.utils import timezone

logger = logging.getLogger('deprecation')

class DeprecationWarningMiddleware:
    """Log and warn about deprecated API usage."""

    DEPRECATED_PATHS = {
        '/api/auth/': {'sunset': '2026-06-01', 'replacement': '/api/v1/auth/'},
        '/api/procurement/': {'sunset': '2026-06-01', 'replacement': '/api/v1/procurement/'},
        '/api/analytics/': {'sunset': '2026-06-01', 'replacement': '/api/v1/analytics/'},
        '/api/reports/': {'sunset': '2026-06-01', 'replacement': '/api/v1/reports/'},
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        for path, info in self.DEPRECATED_PATHS.items():
            if request.path.startswith(path):
                logger.warning(
                    f"Deprecated API used: {request.path} "
                    f"(sunset: {info['sunset']}, use: {info['replacement']})",
                    extra={
                        'path': request.path,
                        'user': getattr(request.user, 'username', 'anonymous'),
                        'ip': request.META.get('REMOTE_ADDR'),
                    }
                )
                response = self.get_response(request)
                response['Deprecation'] = f"sunset={info['sunset']}"
                response['Link'] = f"<{info['replacement']}>; rel=\"successor-version\""
                return response

        return self.get_response(request)
```

**Add to settings:**

```python
# backend/config/settings.py
MIDDLEWARE = [
    # ... existing middleware ...
    'apps.core.middleware.DeprecationWarningMiddleware',
]
```

---

## 4. Task Queue Prevention

### 4.1 Celery Task Standards

**Every task MUST have:**

```python
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    acks_late=True,
    reject_on_worker_lost=True,
)
def my_task(self, arg1, arg2):
    """
    Task description here.

    Args:
        arg1: Description
        arg2: Description

    Returns:
        Description of return value

    Raises:
        SpecificException: When this happens
    """
    logger.info(f"Task {self.request.id} started", extra={
        'task_id': self.request.id,
        'arg1': arg1,
        'arg2': arg2,
    })

    try:
        result = do_work(arg1, arg2)
        logger.info(f"Task {self.request.id} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Task {self.request.id} failed: {e}", exc_info=True)
        raise
```

### 4.2 Task Result Backend

**Enable result tracking:**

```python
# backend/config/celery.py
app.conf.update(
    result_backend='redis://redis:6379/0',
    result_expires=86400,  # 24 hours
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
)
```

### 4.3 Flower Monitoring

**Add to docker-compose.yml:**

```yaml
services:
  flower:
    image: mher/flower:0.9.7
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - FLOWER_BASIC_AUTH=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin}
    depends_on:
      - redis
      - celery
    networks:
      - app-network
```

**Dashboard URL:** `http://localhost:5555/`

---

## 5. Frontend Debt Prevention

### 5.1 Bundle Size Budgets

**Setup bundlesize:**

```bash
cd frontend
pnpm add -D bundlesize
```

**package.json:**

```json
{
  "bundlesize": [
    {
      "path": "./dist/assets/index-*.js",
      "maxSize": "200 kB"
    },
    {
      "path": "./dist/assets/vendor-*.js",
      "maxSize": "300 kB"
    },
    {
      "path": "./dist/assets/vendor-charts-*.js",
      "maxSize": "500 kB"
    }
  ],
  "scripts": {
    "bundlesize": "bundlesize"
  }
}
```

**CI Check:**

```yaml
# .github/workflows/ci.yml
- name: Check bundle sizes
  run: |
    cd frontend
    pnpm build
    pnpm bundlesize
```

### 5.2 Query Key Factory Pattern

**Standard pattern for all TanStack Query keys:**

```typescript
// frontend/src/lib/queryKeys.ts
export const queryKeys = {
  analytics: {
    all: ['analytics'] as const,
    overview: (orgId: number) => ['analytics', 'overview', orgId] as const,
    pareto: (orgId: number) => ['analytics', 'pareto', orgId] as const,
    suppliers: (orgId: number) => ['analytics', 'suppliers', orgId] as const,
    categories: (orgId: number) => ['analytics', 'categories', orgId] as const,
    trends: (orgId: number, year?: number) => ['analytics', 'trends', orgId, year] as const,
  },
  procurement: {
    all: ['procurement'] as const,
    transactions: (orgId: number, filters?: object) => ['procurement', 'transactions', orgId, filters] as const,
    suppliers: (orgId: number) => ['procurement', 'suppliers', orgId] as const,
    categories: (orgId: number) => ['procurement', 'categories', orgId] as const,
  },
  reports: {
    all: ['reports'] as const,
    list: (orgId: number) => ['reports', 'list', orgId] as const,
    detail: (reportId: string) => ['reports', 'detail', reportId] as const,
    schedules: (orgId: number) => ['reports', 'schedules', orgId] as const,
  },
  filters: {
    all: ['filters'] as const,
    presets: ['filters', 'presets'] as const,
  },
  p2p: {
    all: ['p2p'] as const,
    cycle: (orgId: number) => ['p2p', 'cycle', orgId] as const,
    matching: (orgId: number) => ['p2p', 'matching', orgId] as const,
    aging: (orgId: number) => ['p2p', 'aging', orgId] as const,
  },
} as const;
```

**Usage:**

```typescript
// Good
const { data } = useQuery({
  queryKey: queryKeys.analytics.overview(activeOrganization?.id ?? 0),
  queryFn: () => analyticsAPI.getOverview(),
});

// Bad - avoid inline arrays
const { data } = useQuery({
  queryKey: ['analytics', 'overview', activeOrganization?.id],
  queryFn: () => analyticsAPI.getOverview(),
});
```

### 5.3 Component File Size Limits

**ESLint rule (add to .eslintrc.js):**

```javascript
module.exports = {
  rules: {
    'max-lines': ['warn', { max: 300, skipBlankLines: true, skipComments: true }],
    'max-lines-per-function': ['warn', { max: 100, skipBlankLines: true, skipComments: true }],
  },
};
```

---

## 6. Database Prevention

### 6.1 Index Guidelines

**Every new model must consider:**

```python
class MyModel(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        indexes = [
            # Always index organization for multi-tenancy
            models.Index(fields=['organization']),

            # Index common filter combinations
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['organization', 'category']),

            # Index for sorting patterns
            models.Index(fields=['organization', '-date']),
            models.Index(fields=['organization', '-amount']),
        ]
```

### 6.2 Query Analysis in Development

**Add to Django settings (development only):**

```python
if DEBUG:
    LOGGING['loggers']['django.db.backends'] = {
        'level': 'DEBUG',
        'handlers': ['console'],
    }
```

**Or use django-debug-toolbar:**

```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1']
```

---

## 7. Documentation as Prevention

### 7.1 CONTRIBUTING.md Checklist

Add to `CONTRIBUTING.md`:

```markdown
## Pull Request Checklist

### Before Submitting

#### Code Quality
- [ ] No service file exceeds 500 lines
- [ ] No component file exceeds 300 lines
- [ ] All new endpoints have TypeScript types
- [ ] Query keys use the factory pattern from `lib/queryKeys.ts`

#### Performance
- [ ] New database queries have appropriate indexes
- [ ] Aggregation queries use caching where appropriate
- [ ] Checked endpoint response time with django-silk

#### Debt Prevention
- [ ] No "temporary" code without a sunset date comment
- [ ] Magic numbers are in constants (not inline)
- [ ] Celery tasks have proper error handling and logging

#### Documentation
- [ ] New features documented in relevant docs/
- [ ] API changes reflected in OpenAPI schema
- [ ] Breaking changes noted in CHANGELOG.md
```

### 7.2 ADR (Architecture Decision Records)

Create `docs/adr/` folder for significant decisions:

```markdown
# docs/adr/001-multi-org-support.md

# ADR 001: Multi-Organization User Support

## Status
Accepted

## Context
Users needed to belong to multiple organizations with different roles.

## Decision
Implemented `UserOrganizationMembership` model with signals to sync with `UserProfile`.

## Consequences
- Users can now have different roles per organization
- Added complexity in permission checking
- Legacy `UserProfile.organization` maintained for backwards compatibility
```

---

## 8. Automated Prevention Tools

### 8.1 Pre-commit Hooks

**Setup:**

```bash
pip install pre-commit
pre-commit install
```

**.pre-commit-config.yaml:**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=500']

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: local
    hooks:
      - id: check-service-size
        name: Check service file sizes
        entry: bash -c 'find backend/apps -name "services.py" | xargs wc -l | awk "{if (\$1 > 500 && \$2 != \"total\") {print \"ERROR: \" \$2 \" exceeds 500 lines\"; exit 1}}"'
        language: system
        pass_filenames: false
```

### 8.2 GitHub Actions Workflow

```yaml
# .github/workflows/debt-prevention.yml
name: Debt Prevention Checks

on:
  pull_request:
    branches: [master, main]

jobs:
  check-debt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check service file sizes
        run: |
          echo "Checking service file sizes..."
          failed=0
          for file in $(find backend/apps -name "services.py" -o -name "*_services.py"); do
            lines=$(wc -l < "$file")
            if [ "$lines" -gt 500 ]; then
              echo "::error file=$file::Service file exceeds 500 lines ($lines)"
              failed=1
            fi
          done
          exit $failed

      - name: Check for TODO without dates
        run: |
          echo "Checking for TODOs without sunset dates..."
          # Find TODOs that don't have a version or date
          if grep -rn "TODO:" --include="*.py" --include="*.ts" --include="*.tsx" | grep -v "TODO:.*v[0-9]" | grep -v "TODO:.*202[0-9]"; then
            echo "::warning::Found TODOs without version or date targets"
          fi

      - name: Check for magic numbers
        run: |
          echo "Checking for common magic numbers..."
          # Check for hard-coded thresholds
          if grep -rn "= 50000\|= 100\|= 30/" --include="*.py" backend/apps/; then
            echo "::warning::Found potential magic numbers - consider moving to constants"
          fi
```

---

## 9. Quarterly Debt Review Process

### 9.1 Review Checklist

**Every quarter, review:**

1. **TECHNICAL_DEBT.md** - Update status of all items
2. **Sunset dates** - Remove any passed deadlines
3. **Service sizes** - Split any approaching 500 lines
4. **Bundle sizes** - Check for growth
5. **Query performance** - Review django-silk logs
6. **Dependency versions** - Check for security updates

### 9.2 Debt Budget

**Rule:** Each sprint can add at most 1 new debt item, and must resolve at least 1 existing item.

**Exception process:**
1. Document in PR why debt is necessary
2. Add to `TECHNICAL_DEBT.md` with tracking ID
3. Set sunset date (max 6 months)
4. Get tech lead approval

---

## 10. Quick Reference

### Prevention Checklist (Print This)

```
BEFORE EVERY PR:
[ ] Service files < 500 lines?
[ ] New queries have indexes?
[ ] TypeScript types generated?
[ ] Celery tasks have error handling?
[ ] Magic numbers in constants?
[ ] "Temporary" code has sunset date?
[ ] Bundle size within budget?
[ ] Query keys use factory?
```

### Key Files

| File | Purpose |
|------|---------|
| `docs/TECHNICAL_DEBT.md` | Track all known debt |
| `docs/DEBT_PREVENTION.md` | This guide |
| `CONTRIBUTING.md` | PR checklist |
| `.pre-commit-config.yaml` | Automated checks |
| `.github/workflows/debt-prevention.yml` | CI checks |

---

**Last Updated:** 2026-01-08
**Next Review:** 2026-04-08 (Quarterly)
