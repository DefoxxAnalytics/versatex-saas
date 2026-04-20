# Repository Pattern Implementation Plan

## Executive Summary

This plan outlines a phased approach to implementing the Repository Pattern in Versatex Analytics, abstracting data access from Django ORM to enable easier data source switching, improved testability, and cleaner architecture.

**Current State:** Services use direct Django ORM calls (~200+ occurrences across 4,500+ lines of service code)
**Target State:** Services depend on repository interfaces; concrete implementations use Django ORM (swappable to other data sources)

---

## Phase 1: Foundation

### 1.1 Create Repository Infrastructure

**New Directory Structure:**
```
backend/apps/
├── core/                           # NEW: Shared infrastructure
│   ├── __init__.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract base repository
│   │   ├── interfaces.py           # Repository protocols/interfaces
│   │   └── exceptions.py           # Repository-specific exceptions
│   └── registry.py                 # Dependency injection registry
├── procurement/
│   ├── repositories/               # NEW
│   │   ├── __init__.py
│   │   ├── transaction.py          # TransactionRepository
│   │   ├── supplier.py             # SupplierRepository
│   │   ├── category.py             # CategoryRepository
│   │   └── contract.py             # ContractRepository
│   └── ...
└── analytics/
    ├── repositories/               # NEW (P2P-specific)
    │   ├── __init__.py
    │   ├── invoice.py              # InvoiceRepository
    │   ├── purchase_order.py       # PurchaseOrderRepository
    │   ├── purchase_requisition.py # PurchaseRequisitionRepository
    │   └── goods_receipt.py        # GoodsReceiptRepository
    └── ...
```

### 1.2 Base Repository Interface

**File: `backend/apps/core/repositories/base.py`**

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

T = TypeVar('T')

@dataclass
class FilterParams:
    """Standard filter parameters used across all repositories."""
    organization_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    fiscal_year: Optional[int] = None
    supplier_ids: Optional[List[int]] = None
    category_ids: Optional[List[int]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None

@dataclass
class PaginationParams:
    """Pagination parameters."""
    page: int = 1
    page_size: int = 50

@dataclass
class AggregateResult:
    """Standard aggregation result."""
    total: Decimal
    count: int
    average: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None

class BaseRepository(ABC, Generic[T]):
    """Abstract base repository defining common operations."""

    @abstractmethod
    def get_by_id(self, id: int, organization_id: int) -> Optional[T]:
        """Get single entity by ID, scoped to organization."""
        pass

    @abstractmethod
    def get_all(self, filters: FilterParams, pagination: Optional[PaginationParams] = None) -> List[T]:
        """Get all entities matching filters."""
        pass

    @abstractmethod
    def count(self, filters: FilterParams) -> int:
        """Count entities matching filters."""
        pass

    @abstractmethod
    def exists(self, id: int, organization_id: int) -> bool:
        """Check if entity exists."""
        pass

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        """Create new entity."""
        pass

    @abstractmethod
    def update(self, id: int, data: Dict[str, Any]) -> T:
        """Update existing entity."""
        pass

    @abstractmethod
    def delete(self, id: int, organization_id: int) -> bool:
        """Delete entity."""
        pass
```

### 1.3 Analytics-Specific Interfaces

**File: `backend/apps/core/repositories/interfaces.py`**

```python
from abc import abstractmethod
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import date
from .base import BaseRepository, FilterParams, AggregateResult

class ITransactionRepository(BaseRepository):
    """Interface for transaction data access."""

    @abstractmethod
    def get_total_spend(self, filters: FilterParams) -> Decimal:
        """Get total spend amount."""
        pass

    @abstractmethod
    def get_spend_by_category(self, filters: FilterParams, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get spend grouped by category."""
        pass

    @abstractmethod
    def get_spend_by_supplier(self, filters: FilterParams, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get spend grouped by supplier."""
        pass

    @abstractmethod
    def get_monthly_trend(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get monthly spend trend."""
        pass

    @abstractmethod
    def get_pareto_data(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get Pareto (80/20) analysis data."""
        pass

    @abstractmethod
    def get_stratification_data(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get spend stratification by bands."""
        pass

    @abstractmethod
    def get_tail_spend_data(self, filters: FilterParams, threshold: Decimal) -> Dict[str, Any]:
        """Get tail spend analysis."""
        pass

    @abstractmethod
    def get_seasonality_data(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get seasonality patterns."""
        pass

    @abstractmethod
    def get_year_over_year_data(self, filters: FilterParams, year1: int, year2: int) -> Dict[str, Any]:
        """Get year-over-year comparison."""
        pass


class ISupplierRepository(BaseRepository):
    """Interface for supplier data access."""

    @abstractmethod
    def get_with_spend(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get suppliers with aggregated spend."""
        pass

    @abstractmethod
    def get_top_suppliers(self, filters: FilterParams, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top suppliers by spend."""
        pass

    @abstractmethod
    def get_supplier_concentration(self, filters: FilterParams) -> Dict[str, Any]:
        """Get supplier concentration metrics."""
        pass


class ICategoryRepository(BaseRepository):
    """Interface for category data access."""

    @abstractmethod
    def get_with_spend(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get categories with aggregated spend."""
        pass

    @abstractmethod
    def get_category_hierarchy(self, organization_id: int) -> List[Dict[str, Any]]:
        """Get category tree structure."""
        pass


class IInvoiceRepository(BaseRepository):
    """Interface for invoice data access (P2P)."""

    @abstractmethod
    def get_aging_buckets(self, filters: FilterParams) -> Dict[str, Decimal]:
        """Get AP aging by buckets (Current, 31-60, 61-90, 90+)."""
        pass

    @abstractmethod
    def get_matching_status(self, filters: FilterParams) -> Dict[str, Any]:
        """Get 3-way matching statistics."""
        pass

    @abstractmethod
    def get_exceptions(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get matching exceptions."""
        pass

    @abstractmethod
    def get_dpo_trends(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get Days Payable Outstanding trends."""
        pass


class IPurchaseOrderRepository(BaseRepository):
    """Interface for purchase order data access (P2P)."""

    @abstractmethod
    def get_cycle_times(self, filters: FilterParams) -> Dict[str, Any]:
        """Get PR→PO cycle time metrics."""
        pass

    @abstractmethod
    def get_contract_coverage(self, filters: FilterParams) -> Dict[str, Any]:
        """Get contract backing statistics."""
        pass

    @abstractmethod
    def get_maverick_spend(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get non-compliant/maverick spend."""
        pass

    @abstractmethod
    def get_amendment_analysis(self, filters: FilterParams) -> Dict[str, Any]:
        """Get PO amendment patterns."""
        pass


class IPurchaseRequisitionRepository(BaseRepository):
    """Interface for PR data access (P2P)."""

    @abstractmethod
    def get_approval_metrics(self, filters: FilterParams) -> Dict[str, Any]:
        """Get approval time and rate metrics."""
        pass

    @abstractmethod
    def get_by_department(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get PRs grouped by department."""
        pass

    @abstractmethod
    def get_pending_approvals(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get PRs pending approval."""
        pass


class IContractRepository(BaseRepository):
    """Interface for contract data access."""

    @abstractmethod
    def get_utilization(self, filters: FilterParams) -> List[Dict[str, Any]]:
        """Get contract utilization rates."""
        pass

    @abstractmethod
    def get_expiring_soon(self, organization_id: int, days: int = 90) -> List[Dict[str, Any]]:
        """Get contracts expiring within N days."""
        pass

    @abstractmethod
    def get_compliance_status(self, filters: FilterParams) -> Dict[str, Any]:
        """Get contract compliance overview."""
        pass
```

---

## Phase 2: Core Repositories

### 2.1 TransactionRepository (Highest Priority)

**File: `backend/apps/procurement/repositories/transaction.py`**

This is the most critical repository - used by 30+ methods in AnalyticsService.

**Key Methods to Implement:**
| Method | Current Location | ORM Pattern |
|--------|-----------------|-------------|
| `get_total_spend()` | services.py:89 | `Transaction.objects.filter(...).aggregate(Sum('amount'))` |
| `get_spend_by_category()` | services.py:112 | `.values('category__name').annotate(total=Sum('amount'))` |
| `get_spend_by_supplier()` | services.py:145 | `.values('supplier__name').annotate(total=Sum('amount'))` |
| `get_monthly_trend()` | services.py:178 | `.annotate(month=TruncMonth('date')).values('month')` |
| `get_pareto_data()` | services.py:245 | Complex: cumulative sum + percentile calculation |
| `get_stratification_data()` | services.py:312 | `.annotate(band=Case(When(...)))` with spend bands |
| `get_tail_spend_data()` | services.py:398 | Threshold-based filtering + aggregation |
| `get_seasonality_data()` | services.py:456 | Monthly grouping + seasonal index calculation |
| `get_year_over_year_data()` | services.py:534 | Dual-year queries + variance calculation |

**Implementation Strategy:**
```python
# backend/apps/procurement/repositories/transaction.py
from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Case, When, Value, Q
from django.db.models.functions import TruncMonth, ExtractMonth, ExtractYear, Coalesce
from apps.core.repositories.interfaces import ITransactionRepository
from apps.core.repositories.base import FilterParams, PaginationParams
from apps.procurement.models import Transaction

class DjangoTransactionRepository(ITransactionRepository):
    """Django ORM implementation of TransactionRepository."""

    def _build_queryset(self, filters: FilterParams):
        """Build base queryset with standard filters."""
        qs = Transaction.objects.filter(organization_id=filters.organization_id)

        if filters.start_date:
            qs = qs.filter(date__gte=filters.start_date)
        if filters.end_date:
            qs = qs.filter(date__lte=filters.end_date)
        if filters.fiscal_year:
            # Fiscal year: July 1 - June 30
            fy_start = date(filters.fiscal_year - 1, 7, 1)
            fy_end = date(filters.fiscal_year, 6, 30)
            qs = qs.filter(date__range=(fy_start, fy_end))
        if filters.supplier_ids:
            qs = qs.filter(supplier_id__in=filters.supplier_ids)
        if filters.category_ids:
            qs = qs.filter(category_id__in=filters.category_ids)
        if filters.min_amount:
            qs = qs.filter(amount__gte=filters.min_amount)
        if filters.max_amount:
            qs = qs.filter(amount__lte=filters.max_amount)

        return qs

    def get_total_spend(self, filters: FilterParams) -> Decimal:
        result = self._build_queryset(filters).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'))
        )
        return result['total']

    def get_spend_by_category(self, filters: FilterParams, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        qs = self._build_queryset(filters).values(
            'category_id',
            'category__name'
        ).annotate(
            total_spend=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-total_spend')

        if limit:
            qs = qs[:limit]

        return list(qs)

    # ... (implement remaining methods)
```

### 2.2 InvoiceRepository (P2P Critical Path)

**File: `backend/apps/analytics/repositories/invoice.py`**

**Key Methods (from p2p_services.py):**
| Method | Lines | Purpose |
|--------|-------|---------|
| `get_aging_buckets()` | 1245-1298 | AP aging analysis |
| `get_matching_status()` | 456-512 | 3-way match rates |
| `get_exceptions()` | 523-589 | Match exceptions list |
| `get_dpo_trends()` | 1312-1378 | Days Payable Outstanding |

### 2.3 PurchaseOrderRepository

**File: `backend/apps/analytics/repositories/purchase_order.py`**

**Key Methods (from p2p_services.py):**
| Method | Lines | Purpose |
|--------|-------|---------|
| `get_cycle_times()` | 156-234 | PR→PO timing |
| `get_contract_coverage()` | 678-745 | Contract backing % |
| `get_maverick_spend()` | 756-823 | Non-compliant POs |
| `get_amendment_analysis()` | 834-912 | Amendment patterns |

### 2.4 SupplierRepository & CategoryRepository

Lower complexity - mainly aggregation wrappers.

---

## Phase 3: Service Layer Refactoring

### 3.1 Dependency Injection Setup

**File: `backend/apps/core/registry.py`**

```python
from typing import Dict, Type, Any
from apps.core.repositories.interfaces import (
    ITransactionRepository,
    ISupplierRepository,
    ICategoryRepository,
    IInvoiceRepository,
    IPurchaseOrderRepository,
    IPurchaseRequisitionRepository,
    IContractRepository,
)

class RepositoryRegistry:
    """Simple dependency injection container for repositories."""

    _instances: Dict[Type, Any] = {}
    _factories: Dict[Type, Type] = {}

    @classmethod
    def register(cls, interface: Type, implementation: Type):
        """Register an implementation for an interface."""
        cls._factories[interface] = implementation

    @classmethod
    def get(cls, interface: Type) -> Any:
        """Get or create repository instance."""
        if interface not in cls._instances:
            if interface not in cls._factories:
                raise ValueError(f"No implementation registered for {interface}")
            cls._instances[interface] = cls._factories[interface]()
        return cls._instances[interface]

    @classmethod
    def clear(cls):
        """Clear all instances (useful for testing)."""
        cls._instances.clear()

# Default registrations (Django ORM)
def setup_default_repositories():
    from apps.procurement.repositories.transaction import DjangoTransactionRepository
    from apps.procurement.repositories.supplier import DjangoSupplierRepository
    from apps.procurement.repositories.category import DjangoCategoryRepository
    from apps.analytics.repositories.invoice import DjangoInvoiceRepository
    from apps.analytics.repositories.purchase_order import DjangoPurchaseOrderRepository
    from apps.analytics.repositories.purchase_requisition import DjangoPurchaseRequisitionRepository
    from apps.procurement.repositories.contract import DjangoContractRepository

    RepositoryRegistry.register(ITransactionRepository, DjangoTransactionRepository)
    RepositoryRegistry.register(ISupplierRepository, DjangoSupplierRepository)
    RepositoryRegistry.register(ICategoryRepository, DjangoCategoryRepository)
    RepositoryRegistry.register(IInvoiceRepository, DjangoInvoiceRepository)
    RepositoryRegistry.register(IPurchaseOrderRepository, DjangoPurchaseOrderRepository)
    RepositoryRegistry.register(IPurchaseRequisitionRepository, DjangoPurchaseRequisitionRepository)
    RepositoryRegistry.register(IContractRepository, DjangoContractRepository)
```

### 3.2 Refactor AnalyticsService

**Current Pattern (services.py):**
```python
class AnalyticsService:
    def __init__(self, organization):
        self.organization = organization

    def get_spend_by_category(self, start_date=None, end_date=None, ...):
        queryset = Transaction.objects.filter(organization=self.organization)
        # Direct ORM query
```

**Refactored Pattern:**
```python
class AnalyticsService:
    def __init__(
        self,
        organization,
        transaction_repo: ITransactionRepository = None,
        supplier_repo: ISupplierRepository = None,
        category_repo: ICategoryRepository = None,
    ):
        self.organization = organization
        self._transaction_repo = transaction_repo or RepositoryRegistry.get(ITransactionRepository)
        self._supplier_repo = supplier_repo or RepositoryRegistry.get(ISupplierRepository)
        self._category_repo = category_repo or RepositoryRegistry.get(ICategoryRepository)

    def get_spend_by_category(self, start_date=None, end_date=None, ...):
        filters = FilterParams(
            organization_id=self.organization.id,
            start_date=start_date,
            end_date=end_date,
            ...
        )
        return self._transaction_repo.get_spend_by_category(filters)
```

### 3.3 Refactor P2PAnalyticsService

Same pattern as AnalyticsService, injecting P2P-specific repositories.

---

## Phase 4: Testing Infrastructure

### 4.1 Mock Repository Implementations

**File: `backend/apps/core/repositories/mocks.py`**

```python
from typing import List, Dict, Any, Optional
from decimal import Decimal
from apps.core.repositories.interfaces import ITransactionRepository
from apps.core.repositories.base import FilterParams

class MockTransactionRepository(ITransactionRepository):
    """In-memory mock for testing."""

    def __init__(self, data: List[Dict[str, Any]] = None):
        self._data = data or []

    def set_data(self, data: List[Dict[str, Any]]):
        """Set mock data for tests."""
        self._data = data

    def get_total_spend(self, filters: FilterParams) -> Decimal:
        return sum(d['amount'] for d in self._data)

    def get_spend_by_category(self, filters: FilterParams, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        # Simple grouping logic for testing
        by_category = {}
        for item in self._data:
            cat = item.get('category_name', 'Unknown')
            by_category[cat] = by_category.get(cat, Decimal('0')) + item['amount']

        result = [{'category__name': k, 'total_spend': v} for k, v in by_category.items()]
        result.sort(key=lambda x: x['total_spend'], reverse=True)

        if limit:
            result = result[:limit]
        return result

    # ... (implement remaining mock methods)
```

### 4.2 Test Examples

**File: `backend/apps/analytics/tests/test_services_with_repos.py`**

```python
from django.test import TestCase
from decimal import Decimal
from apps.analytics.services import AnalyticsService
from apps.core.repositories.mocks import MockTransactionRepository
from apps.authentication.models import Organization

class TestAnalyticsServiceWithMocks(TestCase):
    """Test AnalyticsService using mock repositories (no DB)."""

    def setUp(self):
        self.org = Organization(id=1, name='Test Org')
        self.mock_repo = MockTransactionRepository()
        self.service = AnalyticsService(
            organization=self.org,
            transaction_repo=self.mock_repo
        )

    def test_get_total_spend(self):
        self.mock_repo.set_data([
            {'amount': Decimal('100.00'), 'category_name': 'IT'},
            {'amount': Decimal('200.00'), 'category_name': 'Office'},
        ])

        result = self.service.get_overview()
        self.assertEqual(result['total_spend'], Decimal('300.00'))

    def test_get_spend_by_category(self):
        self.mock_repo.set_data([
            {'amount': Decimal('100.00'), 'category_name': 'IT'},
            {'amount': Decimal('150.00'), 'category_name': 'IT'},
            {'amount': Decimal('200.00'), 'category_name': 'Office'},
        ])

        result = self.service.get_spend_by_category()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['category__name'], 'IT')
        self.assertEqual(result[0]['total_spend'], Decimal('250.00'))
```

---

## Phase 5: Query Optimizations

### 5.1 Fix N+1 Queries in P2P Module

**Current Issue (p2p_services.py:84-86):**
```python
for pr in prs:
    po = pr.purchase_orders.first()  # N+1 query!
    if po:
        # process...
```

**Fixed in Repository:**
```python
def get_prs_with_related(self, filters: FilterParams) -> List[Dict[str, Any]]:
    return PurchaseRequisition.objects.filter(
        organization_id=filters.organization_id
    ).prefetch_related(
        Prefetch(
            'purchase_orders',
            queryset=PurchaseOrder.objects.select_related('supplier').order_by('-created_at')
        )
    ).annotate(
        first_po_date=Subquery(
            PurchaseOrder.objects.filter(
                requisition=OuterRef('pk')
            ).order_by('created_at').values('created_at')[:1]
        ),
        pr_to_po_days=ExpressionWrapper(
            F('first_po_date') - F('submitted_date'),
            output_field=DurationField()
        )
    )
```

### 5.2 Consolidate Python Aggregations to DB

**Current Issue (p2p_services.py - manual averaging):**
```python
cycle_times = []
for doc in documents:
    cycle_times.append((doc.completed_date - doc.created_date).days)
avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else 0
```

**Fixed in Repository:**
```python
def get_cycle_time_stats(self, filters: FilterParams) -> Dict[str, Any]:
    return PurchaseOrder.objects.filter(
        organization_id=filters.organization_id,
        completed_date__isnull=False
    ).aggregate(
        avg_cycle_days=Avg(
            ExpressionWrapper(
                F('completed_date') - F('created_date'),
                output_field=DurationField()
            )
        ),
        min_cycle_days=Min(...),
        max_cycle_days=Max(...),
        total_count=Count('id')
    )
```

---

## Phase 6: Alternative Data Source (Future)

### 6.1 Example: REST API Repository

```python
# backend/apps/procurement/repositories/transaction_api.py
import httpx
from apps.core.repositories.interfaces import ITransactionRepository

class APITransactionRepository(ITransactionRepository):
    """REST API implementation for external data source."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=base_url,
            headers={'Authorization': f'Bearer {api_key}'}
        )

    def get_total_spend(self, filters: FilterParams) -> Decimal:
        params = self._filters_to_params(filters)
        response = self.client.get('/transactions/total-spend', params=params)
        response.raise_for_status()
        return Decimal(response.json()['total'])

    def get_spend_by_category(self, filters: FilterParams, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        params = self._filters_to_params(filters)
        if limit:
            params['limit'] = limit
        response = self.client.get('/transactions/by-category', params=params)
        response.raise_for_status()
        return response.json()['data']
```

### 6.2 Switch Data Source

```python
# In Django settings or startup:
if settings.USE_EXTERNAL_API:
    RepositoryRegistry.register(
        ITransactionRepository,
        APITransactionRepository
    )
else:
    RepositoryRegistry.register(
        ITransactionRepository,
        DjangoTransactionRepository
    )
```

---

## Implementation Order & Priority

| Priority | Repository | Complexity | Dependencies | Est. Effort |
|----------|-----------|------------|--------------|-------------|
| 1 | TransactionRepository | High | None | 3 days |
| 2 | SupplierRepository | Low | Transaction | 1 day |
| 3 | CategoryRepository | Low | Transaction | 1 day |
| 4 | InvoiceRepository | High | None | 2 days |
| 5 | PurchaseOrderRepository | Medium | Invoice | 2 days |
| 6 | PurchaseRequisitionRepository | Medium | PO | 1 day |
| 7 | ContractRepository | Medium | None | 1 day |
| 8 | GoodsReceiptRepository | Low | PO, Invoice | 1 day |

**Total Estimated Effort:** 12-15 days of development

---

## Migration Strategy

### Gradual Adoption (Recommended)

1. **Phase 1:** Create infrastructure + TransactionRepository
2. **Phase 2:** Refactor AnalyticsService to use TransactionRepository
3. **Phase 3:** Add remaining procurement repositories (Supplier, Category)
4. **Phase 4:** Create P2P repositories (Invoice, PO, PR)
5. **Phase 5:** Refactor P2PAnalyticsService
6. **Phase 6:** Add mock implementations + comprehensive tests
7. **Phase 7:** Performance testing + optimization

### Backward Compatibility

- Keep existing service methods signatures unchanged
- Repositories are injected internally, not exposed to views
- Views continue to instantiate services the same way
- Add `@deprecated` decorator to any methods being phased out

---

## Success Criteria

1. **Testability:** 80%+ service code testable without database
2. **Separation:** Zero direct ORM calls in service layer
3. **Performance:** No regression in query performance (benchmark before/after)
4. **Flexibility:** Ability to swap Django ORM for API source with config change
5. **Coverage:** All existing analytics methods accessible through repositories

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance regression | High | Profile all queries before/after; use `select_related`/`prefetch_related` |
| Breaking existing tests | Medium | Run full test suite after each phase |
| Increased complexity | Medium | Document patterns; create code generation scripts |
| Scope creep | High | Strict phase boundaries; defer optimizations to Phase 5 |

---

## Files to Create

```
backend/apps/core/__init__.py
backend/apps/core/repositories/__init__.py
backend/apps/core/repositories/base.py
backend/apps/core/repositories/interfaces.py
backend/apps/core/repositories/exceptions.py
backend/apps/core/repositories/mocks.py
backend/apps/core/registry.py

backend/apps/procurement/repositories/__init__.py
backend/apps/procurement/repositories/transaction.py
backend/apps/procurement/repositories/supplier.py
backend/apps/procurement/repositories/category.py
backend/apps/procurement/repositories/contract.py

backend/apps/analytics/repositories/__init__.py
backend/apps/analytics/repositories/invoice.py
backend/apps/analytics/repositories/purchase_order.py
backend/apps/analytics/repositories/purchase_requisition.py
backend/apps/analytics/repositories/goods_receipt.py
```

## Files to Modify

```
backend/apps/analytics/services.py          # Inject repositories
backend/apps/analytics/p2p_services.py      # Inject P2P repositories
backend/config/settings.py                  # Add core app, repository config
backend/apps/procurement/tests/             # Add repository tests
backend/apps/analytics/tests/               # Add service tests with mocks
```
