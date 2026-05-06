"""
Phase 5 Task 5.9 — Finding B5

Verifies `P2PAnalyticsService.get_exceptions_by_supplier` uses the abandoned
`Subquery(OuterRef(...))` setup to compute `primary_exception_type` per
supplier in a single query, instead of an N+1 per-supplier loop.

Behavior contract:
- Each row's `primary_exception_type` is the most-frequent `exception_type`
  among that supplier's exception invoices.
- Total ORM queries do not scale linearly with the number of suppliers.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.analytics.p2p_services import P2PAnalyticsService
from apps.procurement.models import Invoice, Supplier


def _make_invoice(organization, supplier, exception_type, idx, has_exception=True):
    today = date.today()
    return Invoice.objects.create(
        organization=organization,
        invoice_number=f'INV-{supplier.code}-{exception_type or "OK"}-{idx}',
        supplier=supplier,
        invoice_date=today - timedelta(days=30),
        due_date=today,
        invoice_amount=Decimal('1000'),
        net_amount=Decimal('1000'),
        status='received',
        has_exception=has_exception,
        exception_type=exception_type if has_exception else '',
        exception_resolved=False,
    )


@pytest.fixture
def suppliers_with_mixed_exceptions(db, organization):
    """Three suppliers each with a different dominant exception_type.

    Supplier A: 5x price_variance, 2x quantity_variance, 1x duplicate
    Supplier B: 4x quantity_variance, 1x price_variance
    Supplier C: 3x duplicate, 2x no_po, 1x missing_gr
    """
    suppliers = {}
    profiles = {
        'A': [
            ('price_variance', 5),
            ('quantity_variance', 2),
            ('duplicate', 1),
        ],
        'B': [
            ('quantity_variance', 4),
            ('price_variance', 1),
        ],
        'C': [
            ('duplicate', 3),
            ('no_po', 2),
            ('missing_gr', 1),
        ],
    }
    expected_primary = {
        'A': 'price_variance',
        'B': 'quantity_variance',
        'C': 'duplicate',
    }

    for letter, distribution in profiles.items():
        sup = Supplier.objects.create(
            organization=organization,
            name=f'Supplier {letter}',
            code=f'SUP-{letter}',
            is_active=True,
        )
        suppliers[letter] = sup
        idx = 0
        for exc_type, count in distribution:
            for _ in range(count):
                _make_invoice(organization, sup, exc_type, idx)
                idx += 1

    return suppliers, expected_primary


@pytest.mark.django_db
class TestPrimaryExceptionTypePerSupplier:

    def test_primary_exception_type_matches_most_frequent_per_supplier(
        self, organization, suppliers_with_mixed_exceptions
    ):
        suppliers, expected_primary = suppliers_with_mixed_exceptions

        service = P2PAnalyticsService(organization)
        result = service.get_exceptions_by_supplier(limit=20)

        by_supplier_id = {row['supplier_id']: row for row in result}
        for letter, sup in suppliers.items():
            assert sup.id in by_supplier_id, f'Supplier {letter} missing from result'
            row = by_supplier_id[sup.id]
            assert row['primary_exception_type'] == expected_primary[letter], (
                f"Supplier {letter}: expected primary "
                f"{expected_primary[letter]!r}, got {row['primary_exception_type']!r}"
            )

    def test_primary_type_with_tie_is_deterministic(self, db, organization):
        """When two exception types tie, MIN/ordering picks the first by name —
        but we only require that *some* dominant type is returned (not None)."""
        sup = Supplier.objects.create(
            organization=organization,
            name='Tie Supplier',
            code='SUP-TIE',
            is_active=True,
        )
        _make_invoice(organization, sup, 'price_variance', 0)
        _make_invoice(organization, sup, 'quantity_variance', 1)

        service = P2PAnalyticsService(organization)
        result = service.get_exceptions_by_supplier(limit=10)

        assert len(result) == 1
        assert result[0]['primary_exception_type'] in {
            'price_variance', 'quantity_variance'
        }


@pytest.mark.django_db
class TestQueryCountElimination:
    """
    The pre-fix loop ran one extra Invoice query per supplier
    (~1 + N + N + 1 queries for N suppliers).
    After wiring the subquery + dropping the per-supplier loop,
    the query count must be bounded by a small constant.
    """

    def test_query_count_does_not_scale_with_supplier_count(self, db, organization):
        for letter in 'ABCDEFGHIJKLMNOPQRST':  # 20 suppliers
            sup = Supplier.objects.create(
                organization=organization,
                name=f'Sup {letter}',
                code=f'S-{letter}',
                is_active=True,
            )
            _make_invoice(organization, sup, 'price_variance', 0)
            _make_invoice(organization, sup, 'price_variance', 1)
            _make_invoice(organization, sup, 'quantity_variance', 2)

        service = P2PAnalyticsService(organization)

        with CaptureQueriesContext(connection) as ctx:
            result = service.get_exceptions_by_supplier(limit=20)

        assert len(result) == 20
        for row in result:
            assert row['primary_exception_type'] == 'price_variance'

        query_count = len(ctx.captured_queries)
        assert query_count <= 3, (
            f'N+1 not eliminated: {query_count} queries for 20 suppliers '
            f'(expected <= 3). Queries: '
            + '\n'.join(q['sql'][:200] for q in ctx.captured_queries)
        )
