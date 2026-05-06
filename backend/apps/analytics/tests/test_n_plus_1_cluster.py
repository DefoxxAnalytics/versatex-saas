"""
Phase 5 Task 5.8 — N+1 cluster regression tests (Findings B1, B2, B6, B7).

Each test class targets one N+1 site that was refactored to single-query
DB-side aggregation. Tests assert two things:

  1. Result shape is identical to (or a strict superset of) the legacy
     loop-based output: same keys, ordering, and types.
  2. `assertNumQueries` (via CaptureQueriesContext) shows the query count
     is bounded by a small constant rather than scaling with the number
     of categories / suppliers / locations.

The N+1 sites covered:
  - B1: SpendAnalyticsService.get_detailed_category_analysis
        (spend.py:96-153 — per-category subcategory queries)
  - B2: ParetoTailAnalyticsService.get_detailed_tail_spend — three loops
        (pareto.py:279-284, :300-307, :343-350)
  - B6/B7: P2PAnalyticsService.get_p2p_cycle_overview
        (p2p_services.py:106-166 — four Python loops over date deltas)
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.analytics.p2p_services import P2PAnalyticsService
from apps.analytics.services.pareto import ParetoTailAnalyticsService
from apps.analytics.services.spend import SpendAnalyticsService
from apps.procurement.models import (
    Category,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    Transaction,
)


# ============================================================================
# B1: SpendAnalyticsService.get_detailed_category_analysis
# ============================================================================

@pytest.fixture
def category_spend_fixture(db, organization, admin_user):
    """N categories x M subcategories x K transactions — designed to expose N+1.

    Pre-fix: 1 (categories agg) + N (per-category subcategory agg) queries.
    Post-fix: 1 (categories agg) + 1 (single GROUP BY (category, subcategory)).
    """
    suppliers = []
    for i in range(3):
        suppliers.append(Supplier.objects.create(
            organization=organization,
            name=f'B1-Sup-{i}',
            code=f'B1S{i}',
            is_active=True,
        ))

    categories = []
    for i in range(8):
        cat = Category.objects.create(
            organization=organization,
            name=f'B1-Cat-{i}',
            description='B1 fixture',
            is_active=True,
        )
        categories.append(cat)
        # 3 subcategories x 2 transactions per category
        for sub_idx in range(3):
            for txn_idx in range(2):
                Transaction.objects.create(
                    organization=organization,
                    supplier=suppliers[txn_idx % len(suppliers)],
                    category=cat,
                    subcategory=f'sub-{sub_idx}',
                    amount=Decimal('1000') * (i + 1) * (sub_idx + 1),
                    date=date.today() - timedelta(days=10 * i),
                    description=f'B1 txn {i}-{sub_idx}-{txn_idx}',
                    uploaded_by=admin_user,
                    upload_batch='b1-fixture',
                )

    return organization, categories


@pytest.mark.django_db
class TestB1CategoryAnalysisShape:
    """Result shape must be unchanged after the N+1 fix."""

    def test_result_keys_are_preserved(self, category_spend_fixture):
        organization, _ = category_spend_fixture
        service = SpendAnalyticsService(organization)
        result = service.get_detailed_category_analysis()

        assert isinstance(result, list)
        assert len(result) == 8
        expected_keys = {
            'category', 'category_id', 'total_spend', 'percent_of_total',
            'transaction_count', 'subcategory_count', 'supplier_count',
            'avg_spend_per_supplier', 'top_subcategory', 'top_subcategory_spend',
            'concentration', 'risk_level', 'subcategories',
        }
        for row in result:
            assert expected_keys.issubset(row.keys())
            assert isinstance(row['subcategories'], list)
            for sub in row['subcategories']:
                assert {
                    'name', 'spend', 'transaction_count',
                    'supplier_count', 'percent_of_category',
                }.issubset(sub.keys())

    def test_subcategories_ordered_by_spend_desc(self, category_spend_fixture):
        organization, _ = category_spend_fixture
        result = SpendAnalyticsService(organization).get_detailed_category_analysis()
        for row in result:
            spends = [s['spend'] for s in row['subcategories']]
            assert spends == sorted(spends, reverse=True), (
                f"Category {row['category']} subcategories not ordered by spend desc: {spends}"
            )

    def test_top_subcategory_matches_first_in_list(self, category_spend_fixture):
        organization, _ = category_spend_fixture
        result = SpendAnalyticsService(organization).get_detailed_category_analysis()
        for row in result:
            if row['subcategories']:
                assert row['top_subcategory'] == row['subcategories'][0]['name']
                assert row['top_subcategory_spend'] == row['subcategories'][0]['spend']


@pytest.mark.django_db
class TestB1CategoryAnalysisQueryCount:
    """Pre-fix: 1 + N queries. Post-fix: <= 3 queries regardless of N."""

    def test_query_count_does_not_scale_with_category_count(
        self, category_spend_fixture
    ):
        organization, categories = category_spend_fixture
        assert len(categories) == 8

        service = SpendAnalyticsService(organization)
        with CaptureQueriesContext(connection) as ctx:
            service.get_detailed_category_analysis()

        # Pre-fix would have been ~9 (1 + 8 categories). Post-fix is 2 queries.
        # Allow a small constant for safety against unrelated query overhead.
        query_count = len(ctx.captured_queries)
        assert query_count <= 3, (
            f'B1 N+1 not eliminated: {query_count} queries for 8 categories '
            f'(expected <= 3).'
        )


# ============================================================================
# B2: ParetoTailAnalyticsService.get_detailed_tail_spend (three loops)
# ============================================================================

@pytest.fixture
def tail_spend_fixture(db, organization, admin_user):
    """Tail/non-tail mix designed to trigger all three consolidation loops.

    - 6 multi-category tail vendors (each <$50K total, >=2 categories)
    - 5 categories with >=3 tail vendors (triggers category consolidation)
    - 5 locations with >=3 tail vendors (triggers geographic consolidation)
    """
    cats = []
    for i in range(5):
        cats.append(Category.objects.create(
            organization=organization,
            name=f'B2-Cat-{i}',
            is_active=True,
        ))

    locations = [f'B2-Loc-{i}' for i in range(5)]
    suppliers = []
    for i in range(15):  # 15 tail vendors
        sup = Supplier.objects.create(
            organization=organization,
            name=f'B2-Sup-{i}',
            code=f'B2S{i}',
            is_active=True,
        )
        suppliers.append(sup)

        # Spread across 2-3 categories per supplier ($1K each = under $50K threshold)
        cat_indices = [i % len(cats), (i + 1) % len(cats)]
        if i % 3 == 0:
            cat_indices.append((i + 2) % len(cats))

        # Spread across 2 locations per supplier
        loc_indices = [i % len(locations), (i + 1) % len(locations)]

        for cat_idx in cat_indices:
            for loc_idx in loc_indices:
                Transaction.objects.create(
                    organization=organization,
                    supplier=sup,
                    category=cats[cat_idx],
                    location=locations[loc_idx],
                    amount=Decimal('1000'),
                    date=date.today() - timedelta(days=5),
                    description=f'B2 txn {i}',
                    uploaded_by=admin_user,
                    upload_batch='b2-fixture',
                )

    # Add one non-tail vendor (>$50K) so the high-spend bucket is non-empty
    big_sup = Supplier.objects.create(
        organization=organization,
        name='B2-Big-Sup',
        code='B2BIG',
        is_active=True,
    )
    Transaction.objects.create(
        organization=organization,
        supplier=big_sup,
        category=cats[0],
        location=locations[0],
        amount=Decimal('60000'),
        date=date.today() - timedelta(days=5),
        description='B2 big txn',
        uploaded_by=admin_user,
        upload_batch='b2-fixture',
    )

    return organization, suppliers, cats, locations


@pytest.mark.django_db
class TestB2TailSpendShape:
    def test_result_keys_are_preserved(self, tail_spend_fixture):
        organization, *_ = tail_spend_fixture
        result = ParetoTailAnalyticsService(organization).get_detailed_tail_spend()

        assert {'summary', 'segments', 'pareto_data', 'category_analysis',
                'consolidation_opportunities'}.issubset(result.keys())
        ops = result['consolidation_opportunities']
        assert {'total_opportunities', 'total_savings', 'top_type',
                'multi_category', 'category', 'geographic'}.issubset(ops.keys())

        # Multi-category vendors keep the same per-row contract
        for row in ops['multi_category']:
            assert {'supplier', 'supplier_id', 'categories', 'category_count',
                    'total_spend', 'savings_potential'}.issubset(row.keys())
            assert isinstance(row['categories'], list)
            assert len(row['categories']) >= 1

        for row in ops['category']:
            assert {'category', 'category_id', 'tail_vendors', 'total_vendors',
                    'tail_spend', 'top_vendor', 'savings_potential'}.issubset(row.keys())
            assert isinstance(row['top_vendor'], str)

        for row in ops['geographic']:
            assert {'location', 'tail_vendors', 'total_vendors', 'tail_spend',
                    'top_vendor', 'savings_potential'}.issubset(row.keys())

    def test_consolidation_buckets_populated(self, tail_spend_fixture):
        organization, *_ = tail_spend_fixture
        result = ParetoTailAnalyticsService(organization).get_detailed_tail_spend()
        ops = result['consolidation_opportunities']

        # Fixture is constructed so each loop produces results.
        assert len(ops['multi_category']) > 0, 'Expected multi-category vendors'
        assert len(ops['category']) > 0, 'Expected category consolidation rows'
        assert len(ops['geographic']) > 0, 'Expected geographic consolidation rows'


@pytest.mark.django_db
class TestB2TailSpendQueryCount:
    """Pre-fix: O(tail_vendors + categories + locations) queries.

    Post-fix: bounded constant (~10 base queries for the analytics aggs +
    one per consolidation bucket = roughly 13).
    """

    def test_query_count_does_not_scale_with_vendor_count(self, tail_spend_fixture):
        organization, suppliers, cats, locations = tail_spend_fixture
        # Sanity: at least 6 multi-cat tail vendors + 5 cats + 5 locations.
        assert len(suppliers) >= 15

        service = ParetoTailAnalyticsService(organization)
        with CaptureQueriesContext(connection) as ctx:
            service.get_detailed_tail_spend()

        query_count = len(ctx.captured_queries)
        # Pre-fix would be 15 (multi-cat) + 5 (category) + 5 (geographic)
        # = 25+ overlapping with the base ~5. Post-fix should be <= 10.
        assert query_count <= 10, (
            f'B2 N+1 not eliminated: {query_count} queries for 15 tail vendors + '
            f'5 categories + 5 locations (expected <= 10).\n'
            + '\n'.join(q['sql'][:200] for q in ctx.captured_queries)
        )


# ============================================================================
# B6/B7: P2PAnalyticsService.get_p2p_cycle_overview (four loops)
# ============================================================================

@pytest.fixture
def p2p_cycle_fixture(db, organization, admin_user):
    """Build a chain of PR→PO→GR→Invoice (paid) records.

    Each link has a positive day delta so all four stages contribute samples.
    Add enough records that the pre-fix loop would issue many queries.
    """
    sup = Supplier.objects.create(
        organization=organization, name='B6-Sup', code='B6S', is_active=True,
    )
    cat = Category.objects.create(
        organization=organization, name='B6-Cat', is_active=True,
    )

    today = date.today()
    for i in range(10):
        pr = PurchaseRequisition.objects.create(
            organization=organization,
            pr_number=f'PR-B6-{i}',
            requested_by=admin_user,
            category=cat,
            estimated_amount=Decimal('5000'),
            status='converted_to_po',
            created_date=today - timedelta(days=60),
            submitted_date=today - timedelta(days=58),
            approval_date=today - timedelta(days=55),
        )
        po = PurchaseOrder.objects.create(
            organization=organization,
            po_number=f'PO-B6-{i}',
            supplier=sup,
            category=cat,
            total_amount=Decimal('5000'),
            status='closed',
            created_date=today - timedelta(days=52),  # 3 days after approval
            sent_date=today - timedelta(days=50),
            requisition=pr,
        )
        gr = GoodsReceipt.objects.create(
            organization=organization,
            gr_number=f'GR-B6-{i}',
            purchase_order=po,
            received_date=today - timedelta(days=45),  # 5 days after sent
            quantity_ordered=Decimal('10'),
            quantity_received=Decimal('10'),
            quantity_accepted=Decimal('10'),
            amount_received=Decimal('5000'),
            status='accepted',
        )
        Invoice.objects.create(
            organization=organization,
            invoice_number=f'INV-B6-{i}',
            supplier=sup,
            purchase_order=po,
            goods_receipt=gr,
            invoice_amount=Decimal('5000'),
            net_amount=Decimal('5000'),
            invoice_date=today - timedelta(days=43),  # 2 days after received
            due_date=today - timedelta(days=13),
            status='paid',
            paid_date=today - timedelta(days=20),  # 23 days after invoice
        )

    return organization, sup, cat


@pytest.mark.django_db
class TestB6P2PCycleOverviewShape:
    def test_result_keys_are_preserved(self, p2p_cycle_fixture):
        organization, *_ = p2p_cycle_fixture
        result = P2PAnalyticsService(organization).get_p2p_cycle_overview()

        assert 'stages' in result
        assert 'total_cycle' in result
        assert {'pr_to_po', 'po_to_gr', 'gr_to_invoice', 'invoice_to_payment'} \
            == set(result['stages'].keys())

        for stage_name, stage in result['stages'].items():
            assert {'avg_days', 'target_days', 'sample_size', 'status'} \
                .issubset(stage.keys()), f'stage={stage_name}'
            assert isinstance(stage['avg_days'], (int, float))
            assert isinstance(stage['sample_size'], int)
            assert stage['status'] in {'on_track', 'warning', 'critical'}

        tc = result['total_cycle']
        assert {'avg_days', 'target_days', 'status'}.issubset(tc.keys())

    def test_stage_averages_match_fixture_expectations(self, p2p_cycle_fixture):
        organization, *_ = p2p_cycle_fixture
        result = P2PAnalyticsService(organization).get_p2p_cycle_overview()

        # Each PR→PO is 3 days (-55 → -52), PO→GR is 5 days, GR→Inv is 2 days,
        # Inv→Pay is 23 days. All 10 chains identical → averages exact.
        assert result['stages']['pr_to_po']['avg_days'] == 3.0
        assert result['stages']['pr_to_po']['sample_size'] == 10
        assert result['stages']['po_to_gr']['avg_days'] == 5.0
        assert result['stages']['po_to_gr']['sample_size'] == 10
        assert result['stages']['gr_to_invoice']['avg_days'] == 2.0
        assert result['stages']['gr_to_invoice']['sample_size'] == 10
        assert result['stages']['invoice_to_payment']['avg_days'] == 23.0
        assert result['stages']['invoice_to_payment']['sample_size'] == 10
        assert result['total_cycle']['avg_days'] == 33.0


@pytest.mark.django_db
class TestB6P2PCycleOverviewQueryCount:
    """Pre-fix: 4 outer queries + N invoices/POs/GRs/PRs accessed via prefetch.

    Even with prefetch_related, the loop pulled every parent row into Python
    and processed list-by-list. The aggregate should be a single SQL roundtrip
    per stage = 4 queries total.
    """

    def test_query_count_is_bounded(self, p2p_cycle_fixture):
        organization, *_ = p2p_cycle_fixture
        service = P2PAnalyticsService(organization)

        with CaptureQueriesContext(connection) as ctx:
            service.get_p2p_cycle_overview()

        query_count = len(ctx.captured_queries)
        # 4 stages, each with one aggregate query. Allow small overhead.
        assert query_count <= 6, (
            f'B6 N+1 not eliminated: {query_count} queries (expected <= 6).\n'
            + '\n'.join(q['sql'][:200] for q in ctx.captured_queries)
        )

    def test_query_count_does_not_scale_with_chain_count(
        self, db, organization, admin_user
    ):
        """Add 30 more chains and confirm query count stays the same."""
        sup = Supplier.objects.create(
            organization=organization, name='B6-Sup-Bulk', code='B6BULK',
            is_active=True,
        )
        cat = Category.objects.create(
            organization=organization, name='B6-Cat-Bulk', is_active=True,
        )

        today = date.today()
        for i in range(30):
            pr = PurchaseRequisition.objects.create(
                organization=organization, pr_number=f'PR-BULK-{i}',
                requested_by=admin_user, category=cat,
                estimated_amount=Decimal('100'), status='converted_to_po',
                created_date=today - timedelta(days=60),
                submitted_date=today - timedelta(days=58),
                approval_date=today - timedelta(days=55),
            )
            po = PurchaseOrder.objects.create(
                organization=organization, po_number=f'PO-BULK-{i}',
                supplier=sup, category=cat, total_amount=Decimal('100'),
                status='closed',
                created_date=today - timedelta(days=52),
                sent_date=today - timedelta(days=50),
                requisition=pr,
            )
            gr = GoodsReceipt.objects.create(
                organization=organization, gr_number=f'GR-BULK-{i}',
                purchase_order=po, received_date=today - timedelta(days=45),
                quantity_ordered=Decimal('10'), quantity_received=Decimal('10'),
                quantity_accepted=Decimal('10'),
                amount_received=Decimal('100'), status='accepted',
            )
            Invoice.objects.create(
                organization=organization, invoice_number=f'INV-BULK-{i}',
                supplier=sup, purchase_order=po, goods_receipt=gr,
                invoice_amount=Decimal('100'), net_amount=Decimal('100'),
                invoice_date=today - timedelta(days=43),
                due_date=today - timedelta(days=13),
                status='paid', paid_date=today - timedelta(days=20),
            )

        service = P2PAnalyticsService(organization)
        with CaptureQueriesContext(connection) as ctx:
            result = service.get_p2p_cycle_overview()

        query_count = len(ctx.captured_queries)
        assert query_count <= 6, (
            f'B6 N+1 scaling: {query_count} queries with 30 PR chains.'
        )
        # Sanity: the 30 chains are reflected in samples.
        assert result['stages']['pr_to_po']['sample_size'] == 30
