# Technical Debt Assessment

**Assessment Date:** 2026-01-08
**Codebase Version:** v2.6
**Overall Debt Score:** 3/10 (Manageable)

---

## Executive Summary

The Versatex Analytics codebase is relatively young and well-structured. Most identified debt is **preventable** if addressed in the next 2-3 sprints. The biggest risks are the `AnalyticsService` monolith, real-time aggregation performance at scale, and report generators growing unchecked.

---

## High Risk (Will Bite You Soon)

| Area | Debt Risk | Impact | Effort to Fix |
|------|-----------|--------|---------------|
| **Chart Bundle Size** | 548KB `vendor-charts` chunk | Slow initial load, poor mobile UX | Medium |
| **TanStack Query v4** | Deprecated `cacheTime` API | Breaking changes in v5 upgrade | Low |
| **Legacy API Routes** | `/api/auth/`, `/api/procurement/` duplicates | Confusion, double maintenance | Low |
| **Real-time Aggregations** | Heavy `.aggregate()` on every request | 5-10s load times at millions of rows | High |
| **Frontend Type Sync** | Manual TypeScript types vs Django serializers | Runtime crashes on field changes | Medium |
| **Django 5.0.1** | Already outdated (5.1+ available) | Security patches, missed features | Medium |
| **localStorage Auth** | Tokens duplicated in cookies AND localStorage | State sync bugs, security confusion | Medium |

### Remediation

```typescript
// TODO: v3.0 - Remove legacy routes
// File: backend/config/urls.py lines 28-32
// SUNSET DATE: 2026-06-01 (hard deadline)
path('api/auth/', include('apps.authentication.urls')),      // DEPRECATED
path('api/procurement/', include('apps.procurement.urls')),  // DEPRECATED
```

### Performance Scaling Strategy

```python
# Current: Real-time aggregation on every request
# File: apps/analytics/services.py
Transaction.objects.filter(organization=org).aggregate(Sum('amount'))

# Problem: Works for 100K rows, becomes 5-10s at millions of rows

# Solution Options (in order of complexity):
# 1. Add database indexes (TD-005) - Quick win, buys time
# 2. Implement caching layer (Redis) - Medium effort
# 3. Create Materialized Views in PostgreSQL - Recommended for analytics
# 4. Add OLAP database (ClickHouse/TimescaleDB) - For enterprise scale
```

### Frontend Type Generation

```bash
# Current: Manual TypeScript types in frontend/src/lib/api.ts
# Risk: Backend changes break frontend silently

# Solution: Auto-generate from OpenAPI schema
# The codebase already uses drf-spectacular for OpenAPI generation

# Add to CI/CD pipeline:
npx openapi-typescript http://localhost:8001/api/schema/ -o src/lib/api-types.ts

# Or use openapi-typescript-codegen for full client generation
```

```typescript
// TODO: TanStack Query v5 migration
// Replace cacheTime with gcTime
useQuery(QUERY_KEY, loadFilters, {
  staleTime: Infinity,
  cacheTime: Infinity,  // Change to: gcTime: Infinity
});
```

---

## Medium Risk (Next 6-12 Months)

| Area | Debt Risk | Impact | Effort to Fix |
|------|-----------|--------|---------------|
| **AnalyticsService** | 2000+ line monolith | Hard to test, modify, or split | High |
| **P2P Models in procurement app** | Should be separate `p2p` app | Circular imports, confused boundaries | High |
| **Report Generators** | 13 generators with repeated patterns | Copy-paste bugs, inconsistent formatting | Medium |
| **Filter State** | Split between localStorage, React Query, URL | Race conditions, hydration mismatches | Medium |
| **No Database Indexes** | Missing composite indexes on hot queries | Performance degradation at scale | Low |

### AnalyticsService Decomposition Plan

```python
# Current: apps/analytics/services.py (2000+ lines)
class AnalyticsService:
    # 50+ methods covering all domains

# Recommended split:
# apps/analytics/services/spend_analytics.py
class SpendAnalyticsService:
    def get_spend_by_category(self): ...
    def get_spend_by_supplier(self): ...
    def get_spend_stratification(self): ...

# apps/analytics/services/supplier_analytics.py
class SupplierAnalyticsService:
    def get_supplier_drilldown(self): ...
    def get_detailed_supplier_analysis(self): ...
    def get_supplier_consolidation_opportunities(self): ...

# apps/analytics/services/trend_analytics.py
class TrendAnalyticsService:
    def get_seasonality_analysis(self): ...
    def get_year_over_year_comparison(self): ...
    def get_monthly_trend(self): ...
```

### Missing Database Indexes

```python
# Recommended additions to apps/procurement/models.py
class Transaction(models.Model):
    class Meta:
        indexes = [
            # Existing indexes...
            # Add these for common query patterns:
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['organization', 'supplier', 'date']),
            models.Index(fields=['organization', 'category', 'date']),
        ]
```

---

## Lower Risk (But Worth Watching)

| Area | Debt Risk | Impact | Effort to Fix |
|------|-----------|--------|---------------|
| **Tailwind v4** | Very new, ecosystem still adapting | Plugin incompatibilities | Low |
| **Celery Task Sprawl** | Tasks scattered across apps, chained tasks | No centralized retry/monitoring, "black box" failures | Medium |
| **Test Coverage Gaps** | ~40% estimated coverage | Regression risk on refactors | High |
| **Hard-coded Magic Numbers** | Thresholds like `50000`, `20`, `100` | Scattered business logic | Low |
| **PDF/Excel Generators** | No abstraction layer | Vendor lock-in to ReportLab/openpyxl | Medium |

### Celery Task Monitoring

```python
# Current: Tasks scattered with no centralized monitoring
# File: apps/reports/tasks.py, apps/procurement/tasks.py, etc.

# Problem: Chained tasks (Task A → Task B → Task C) fail silently
# Example: Report generation chains data fetch → PDF render → email send
# If step 2 fails, it's hard to debug without proper tracing

# Solution: Add Flower monitoring + structured logging
# docker-compose.yml
services:
  flower:
    image: mher/flower
    command: celery --broker=redis://redis:6379/0 flower
    ports:
      - "5555:5555"

# Add task result backend for debugging
# config/celery.py
app.conf.result_backend = 'redis://redis:6379/0'
app.conf.result_expires = 3600  # 1 hour retention
```

### Magic Numbers to Extract

```python
# Current: Hard-coded throughout codebase
threshold = 50000  # Tail spend threshold
bulk_limit = 100   # Bulk operation limit
rate_limit = '30/m'  # Token refresh rate

# Recommended: Centralize in config
# apps/core/constants.py
class BusinessRules:
    TAIL_SPEND_THRESHOLD = 50000
    BULK_OPERATION_LIMIT = 100

class RateLimits:
    TOKEN_REFRESH = '30/m'
    LOGIN = '5/m'
    UPLOAD = '10/h'
```

---

## Code Smells

### 1. Repeated Organization Filtering Pattern

**Problem:** This pattern appears 50+ times across views:

```python
def get_queryset(self):
    if not hasattr(self.request.user, 'profile'):
        return Model.objects.none()
    return Model.objects.filter(organization=self.request.user.profile.organization)
```

**Solution:** Create a mixin:

```python
# apps/core/mixins.py
class OrganizationFilteredViewSetMixin:
    """Automatically filters queryset by user's organization."""

    def get_queryset(self):
        qs = super().get_queryset()
        if not hasattr(self.request.user, 'profile'):
            return qs.none()
        return qs.filter(organization=self.request.user.profile.organization)
```

### 2. Inconsistent Query Key Patterns

**Problem:**

```typescript
// Inconsistent patterns across the codebase
['analytics', 'overview']           // Array with strings
'filters'                           // Plain string
['analytics', 'pareto', orgId]      // Array with dynamic value
```

**Solution:** Use a query key factory:

```typescript
// lib/queryKeys.ts
export const queryKeys = {
  analytics: {
    all: ['analytics'] as const,
    overview: (orgId: number) => ['analytics', 'overview', orgId] as const,
    pareto: (orgId: number) => ['analytics', 'pareto', orgId] as const,
    suppliers: (orgId: number) => ['analytics', 'suppliers', orgId] as const,
  },
  filters: {
    all: ['filters'] as const,
    presets: ['filters', 'presets'] as const,
  },
  // ...
};
```

### 3. Report Generator Duplication

**Problem:** 13 report generators share ~60% identical code:

```python
# Each generator repeats:
# - Organization branding setup
# - PDF page configuration
# - Table styling
# - Error handling
```

**Solution:** Extract base class:

```python
# apps/reports/generators/base.py
class BaseReportGenerator:
    def __init__(self, organization, filters=None):
        self.organization = organization
        self.branding = organization.get_branding()
        self.filters = filters or {}

    def setup_pdf(self):
        """Common PDF setup with branding."""
        ...

    def add_header(self, canvas, doc):
        """Standard header with logo."""
        ...

    def add_table(self, data, headers, style='default'):
        """Reusable table component."""
        ...

    @abstractmethod
    def generate_content(self):
        """Override in subclasses."""
        pass
```

---

## Debt Prevention Recommendations

### Immediate (Low Effort)

1. Add `# TODO: v3.0 - Remove legacy routes` comments to deprecated code
2. Create this `TECHNICAL_DEBT.md` file (done)
3. Set up bundle analyzer in CI to catch size regressions
4. Add `CODEOWNERS` file to require reviews for critical paths

### Next Quarter

1. Extract `OrganizationFilteredViewSetMixin` base class
2. Split `AnalyticsService` into domain-specific services
3. Migrate query keys to consistent factory pattern
4. Add database query monitoring (django-silk or similar)
5. Upgrade Django to 5.1+
6. **Set up automated TypeScript type generation in CI/CD** (TD-012)
7. **Add Celery Flower monitoring dashboard** (TD-013)
8. **Document and enforce legacy route sunset date** (TD-014)

### Long Term

1. Consider moving P2P models to separate Django app
2. Evaluate moving filter state to URL params (shareable links)
3. Implement streaming for large CSV exports (>10MB)
4. Add contract tests for API stability
5. Increase test coverage to 70%+
6. **Implement Materialized Views or OLAP integration for analytics at scale** (TD-011)

---

## Mitigation Plan

**Goal:** Proactively address high-risk technical debt to ensure scalability and maintainability.

### Sprint 1: Immediate Wins (Low Effort, High Impact)

#### 1.1 Automate Frontend Type Safety (TD-012)

**Problem:** Manual TypeScript types drift from backend serializers.

**Tasks:**
- [ ] Install `openapi-typescript` in frontend: `pnpm add -D openapi-typescript`
- [ ] Add `generate-types` script to `package.json`:
  ```json
  "scripts": {
    "generate-types": "npx openapi-typescript http://localhost:8001/api/schema/ -o src/lib/api-types.generated.ts"
  }
  ```
- [ ] Add pre-commit hook or CI step to verify types are up-to-date
- [ ] Update imports to use generated types

#### 1.2 Database Indexing (TD-005)

**Problem:** Slow queries on Transaction table at scale.

**Tasks:**
- [ ] Create migration to add composite indexes to `apps/procurement/models.py`:
  ```python
  class Meta:
      indexes = [
          models.Index(fields=['organization', 'date']),
          models.Index(fields=['organization', 'supplier', 'date']),
          models.Index(fields=['organization', 'category', 'date']),
      ]
  ```
- [ ] Run migration: `python manage.py makemigrations && python manage.py migrate`
- [ ] Verify query performance improvement with `EXPLAIN ANALYZE`

#### 1.3 Sunset Legacy Routes (TD-014)

**Problem:** Duplicate API maintenance burden.

**Tasks:**
- [ ] Add `@deprecated` warnings to legacy views/docs
- [ ] Add logging middleware to track legacy endpoint usage
- [ ] Schedule removal date: **2026-06-01** (add to project calendar)
- [ ] Notify API consumers of deprecation

---

### Sprint 2-3: Structural Refactoring

#### 2.1 Decompose AnalyticsService (TD-002)

**Problem:** `services.py` is 2000+ lines - too large to maintain.

**Tasks:**
- [ ] Create `backend/apps/analytics/services/` directory structure:
  ```
  services/
  ├── __init__.py           # Re-exports for backwards compatibility
  ├── base.py               # BaseAnalyticsService with shared methods
  ├── spend_analytics.py    # SpendAnalyticsService
  ├── supplier_analytics.py # SupplierAnalyticsService
  └── trend_analytics.py    # TrendAnalyticsService
  ```
- [ ] **Phase 1:** Extract `SpendAnalyticsService` (category/supplier spend methods)
- [ ] **Phase 2:** Extract `TrendAnalyticsService` (seasonality, YoY methods)
- [ ] **Phase 3:** Extract `TailSpendService` (Pareto, tail spend methods)
- [ ] Update `views.py` imports (maintain `AnalyticsService` as facade temporarily)
- [ ] Add unit tests for each new service

#### 2.2 Standardize Frontend Query Keys (TD-008)

**Problem:** Inconsistent React Query keys cause cache issues.

**Tasks:**
- [ ] Create `frontend/src/lib/queryKeys.ts` with factory pattern
- [ ] Refactor Analytics module to use new factory (pilot)
- [ ] Document pattern in `CONTRIBUTING.md` for team adoption
- [ ] Gradually migrate remaining modules

#### 2.3 TanStack Query v5 Migration (TD-003)

**Problem:** Deprecated `cacheTime` API will break on upgrade.

**Tasks:**
- [ ] Update `@tanstack/react-query` to v5
- [ ] Replace all `cacheTime` with `gcTime`
- [ ] Update query/mutation patterns to v5 API
- [ ] Test all data fetching flows

---

### Sprint 4+: Infrastructure & Performance

#### 3.1 Materialized Views for Analytics (TD-011)

**Problem:** Real-time aggregation doesn't scale beyond 100K rows.

**Tasks:**
- [ ] **Analysis:** Profile slowest 3 queries (likely `get_detailed_category_analysis`)
- [ ] **Design:** Create Django model backed by PostgreSQL Materialized View:
  ```python
  class MonthlyCategorySpend(models.Model):
      """Materialized view for pre-aggregated monthly spend by category."""
      organization = models.ForeignKey(Organization, on_delete=models.DO_NOTHING)
      category = models.ForeignKey(Category, on_delete=models.DO_NOTHING)
      month = models.DateField()
      total_spend = models.DecimalField(max_digits=15, decimal_places=2)
      transaction_count = models.IntegerField()

      class Meta:
          managed = False  # Don't create via Django migrations
          db_table = 'mv_monthly_category_spend'
  ```
- [ ] **SQL:** Create materialized view in PostgreSQL
- [ ] **Refresh Strategy:** Celery task to refresh nightly OR on `DataUpload` completion:
  ```python
  @receiver(post_save, sender=DataUpload)
  def refresh_analytics_views(sender, instance, **kwargs):
      if instance.status == 'completed':
          refresh_materialized_views.delay()
  ```

#### 3.2 Celery Monitoring (TD-013)

**Problem:** Task failures are invisible ("black box").

**Tasks:**
- [ ] Add Flower service to `docker-compose.yml`:
  ```yaml
  flower:
    image: mher/flower:0.9.7
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - FLOWER_BASIC_AUTH=admin:${FLOWER_PASSWORD}
    depends_on:
      - redis
      - celery
  ```
- [ ] Configure `CELERY_RESULT_BACKEND` in settings
- [ ] Expose Flower dashboard on protected internal port
- [ ] Add alerting for failed tasks

---

### Verification Plan

#### Automated Checks (Add to CI)

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Type Safety | `pnpm run check` | No `any` type overrides |
| Migration Sync | `python manage.py makemigrations --check` | No new migrations needed |
| Bundle Size | `bundlesize` | `vendor-charts` < 500KB |
| Service Size | Custom script | No service > 500 lines |

#### Manual Verification

| Test | Expected Result |
|------|-----------------|
| Analytics Overview (1M rows) | Response < 500ms after indexing |
| Service Refactor | No regression in Analytics dashboards |
| Type Generation | Frontend builds without manual type fixes |
| Materialized Views | 10x improvement on aggregation queries |

---

## Tracking

### Debt Items by Priority

| ID | Item | Priority | Status | Target Version |
|----|------|----------|--------|----------------|
| TD-001 | Remove legacy API routes | High | Pending | v3.0 |
| TD-002 | Split AnalyticsService | High | Pending | v3.0 |
| TD-003 | TanStack Query v5 migration | Medium | Pending | v2.8 |
| TD-004 | Extract OrganizationFilteredMixin | Medium | Pending | v2.7 |
| TD-005 | Add missing database indexes | Medium | Pending | v2.7 |
| TD-006 | Reduce chart bundle size | Medium | Pending | v2.8 |
| TD-007 | Centralize magic numbers | Low | Pending | v2.8 |
| TD-008 | Standardize query key factory | Low | Pending | v2.8 |
| TD-009 | Django 5.1 upgrade | Medium | Pending | v2.9 |
| TD-010 | Move P2P to separate app | Low | Pending | v4.0 |
| TD-011 | Implement Materialized Views for analytics | High | Pending | v3.0 |
| TD-012 | Auto-generate TypeScript types from OpenAPI | High | Pending | v2.8 |
| TD-013 | Add Celery task monitoring (Flower) | Medium | Pending | v2.8 |
| TD-014 | Set legacy route sunset date (2026-06-01) | High | Pending | v2.7 |

---

## Review Schedule

- **Monthly:** Review this document, update status
- **Quarterly:** Prioritize debt items for upcoming sprints
- **Per Release:** Check for new debt introduced

---

**Last Updated:** 2026-01-08 (Updated with performance scaling and type sync items)
**Next Review:** 2026-02-08
