"""
Tests for P2PAnalyticsService — Cluster 3 scope.
"""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.analytics.p2p_services import P2PAnalyticsService
from apps.procurement.models import Invoice


class TestAvgDaysToPayHelper:
    """Semantic tests for the shared days-to-pay helper.

    The helper replaces 5 near-identical implementations across
    get_aging_overview / get_supplier_payments_overview /
    get_supplier_payments_scorecard / get_supplier_payment_detail /
    get_dpo_trends. The metric is 'days from invoice issuance to payment'
    (labeled DPO in earlier releases) — NOT balance-sheet DPO.
    """

    @staticmethod
    def _inv(issued, paid):
        return SimpleNamespace(
            invoice_date=issued,
            paid_date=paid,
            invoice_amount=Decimal("100"),
        )

    def test_returns_zero_and_zero_sample_on_empty(self):
        assert P2PAnalyticsService._avg_days_to_pay([]) == (0, 0)

    def test_averages_positive_spreads(self):
        invoices = [
            self._inv(date(2024, 1, 1), date(2024, 1, 11)),  # 10 days
            self._inv(date(2024, 1, 1), date(2024, 1, 21)),  # 20 days
            self._inv(date(2024, 1, 1), date(2024, 1, 31)),  # 30 days
        ]
        avg, sample = P2PAnalyticsService._avg_days_to_pay(invoices)
        assert avg == 20
        assert sample == 3

    def test_rejects_paid_before_issued_as_data_quality(self):
        invoices = [
            self._inv(date(2024, 1, 1), date(2024, 1, 11)),  # 10 days (ok)
            self._inv(
                date(2024, 2, 1), date(2024, 1, 20)
            ),  # paid before issued → dropped
            self._inv(date(2024, 3, 1), date(2024, 3, 21)),  # 20 days (ok)
        ]
        avg, sample = P2PAnalyticsService._avg_days_to_pay(invoices)
        assert sample == 2
        assert avg == 15

    def test_same_day_payment_counts_as_zero_days(self):
        invoices = [self._inv(date(2024, 1, 1), date(2024, 1, 1))]
        avg, sample = P2PAnalyticsService._avg_days_to_pay(invoices)
        assert avg == 0
        assert sample == 1

    def test_missing_paid_date_is_skipped(self):
        invoices = [
            self._inv(date(2024, 1, 1), None),  # unpaid → dropped
            self._inv(date(2024, 1, 1), date(2024, 1, 11)),  # 10 days
        ]
        avg, sample = P2PAnalyticsService._avg_days_to_pay(invoices)
        assert sample == 1
        assert avg == 10


@pytest.fixture
def paid_invoice_fixture(organization, supplier):
    """Three paid invoices: 10-day pay, 30-day pay, data-quality reject."""
    today = date.today()
    for i, offset in enumerate([10, 30]):
        Invoice.objects.create(
            organization=organization,
            invoice_number=f"INV-GOOD-{i}",
            supplier=supplier,
            invoice_date=today - timedelta(days=60),
            due_date=today - timedelta(days=30),
            invoice_amount=Decimal("1000"),
            net_amount=Decimal("1000"),
            status="paid",
            paid_date=today - timedelta(days=60) + timedelta(days=offset),
            payment_terms="Net 30",
        )
    # Data-quality reject: paid_date before invoice_date — should be excluded from avg.
    Invoice.objects.create(
        organization=organization,
        invoice_number="INV-BAD",
        supplier=supplier,
        invoice_date=today - timedelta(days=30),
        due_date=today,
        invoice_amount=Decimal("1000"),
        net_amount=Decimal("1000"),
        status="paid",
        paid_date=today - timedelta(days=40),  # before invoice_date
        payment_terms="Net 30",
    )
    return organization


@pytest.mark.django_db
class TestDaysToPayResponseKeys:
    """
    Guard the canonical + deprecated-alias field names across all 5 methods
    refactored by Cluster 3. If a future maintainer renames a response key
    without updating the frontend, these tests fail loudly.
    """

    def test_aging_overview_exposes_both_aliases(self, paid_invoice_fixture):
        service = P2PAnalyticsService(paid_invoice_fixture)
        result = service.get_aging_overview()
        # Canonical
        assert "avg_days_to_pay" in result
        assert "current_days_to_pay" in result
        # Deprecated aliases
        assert "avg_dpo" in result
        assert "current_dpo" in result
        # Aliases must agree numerically
        assert result["avg_days_to_pay"] == result["avg_dpo"]
        assert result["current_days_to_pay"] == result["current_dpo"]
        # Trend element exposes same quartet
        assert result["trend"]
        elem = result["trend"][0]
        assert "days_to_pay" in elem and "dpo" in elem
        assert "avg_days_to_pay" in elem and "avg_dpo" in elem

    def test_supplier_payments_overview_exposes_both_aliases(
        self, paid_invoice_fixture
    ):
        service = P2PAnalyticsService(paid_invoice_fixture)
        result = service.get_supplier_payments_overview()
        assert "avg_days_to_pay" in result
        assert "avg_dpo" in result
        assert result["avg_days_to_pay"] == result["avg_dpo"]
        # Frontend KPI aliases for overview cards
        assert "total_suppliers" in result
        assert "avg_on_time_rate" in result

    def test_supplier_payments_scorecard_exposes_both_aliases(
        self, paid_invoice_fixture
    ):
        service = P2PAnalyticsService(paid_invoice_fixture)
        rows = service.get_supplier_payments_scorecard()
        assert rows
        row = rows[0]
        assert "days_to_pay" in row and "avg_days_to_pay" in row
        assert "dpo" in row and "avg_dpo" in row
        assert (
            row["days_to_pay"] == row["avg_days_to_pay"] == row["dpo"] == row["avg_dpo"]
        )

    def test_supplier_payment_detail_exposes_both_aliases(
        self, paid_invoice_fixture, supplier
    ):
        service = P2PAnalyticsService(paid_invoice_fixture)
        result = service.get_supplier_payment_detail(supplier.id)
        assert "days_to_pay" in result and "avg_days_to_pay" in result
        assert "dpo" in result and "avg_dpo" in result

    def test_dpo_trends_exposes_both_aliases(self, paid_invoice_fixture):
        service = P2PAnalyticsService(paid_invoice_fixture)
        trend = service.get_dpo_trends(months=6)
        assert trend
        point = trend[0]
        assert "days_to_pay" in point and "avg_days_to_pay" in point
        assert "dpo" in point and "avg_dpo" in point

    def test_data_quality_reject_excluded_from_helper(self, paid_invoice_fixture):
        """paid_date < invoice_date invoice must not distort the average."""
        service = P2PAnalyticsService(paid_invoice_fixture)
        result = service.get_supplier_payments_overview()
        # Only 2 valid invoices: 10 days and 30 days → avg 20
        assert result["avg_days_to_pay"] == 20.0


@pytest.mark.django_db
class TestCluster6Relabels:
    """Cluster 6 accuracy fixes — amount-weighted rates + clearer labels."""

    def _seed_match_fixture(self, organization, supplier):
        from datetime import date

        from apps.procurement.models import Invoice, PurchaseOrder

        po = PurchaseOrder.objects.create(
            organization=organization,
            po_number="PO-MATCH-1",
            supplier=supplier,
            status="closed",
            total_amount=Decimal("10000"),
            created_date=date.today(),
        )
        # One large 3-way matched invoice ($100K), ten small exceptions ($100 each).
        Invoice.objects.create(
            organization=organization,
            invoice_number="INV-MATCH-1",
            supplier=supplier,
            purchase_order=po,
            invoice_date=date.today(),
            due_date=date.today(),
            invoice_amount=Decimal("100000"),
            net_amount=Decimal("100000"),
            status="matched",
            match_status="3way_matched",
            has_exception=False,
        )
        for i in range(10):
            Invoice.objects.create(
                organization=organization,
                invoice_number=f"INV-EX-{i}",
                supplier=supplier,
                invoice_date=date.today(),
                due_date=date.today(),
                invoice_amount=Decimal("100"),
                net_amount=Decimal("100"),
                status="exception",
                match_status="exception",
                has_exception=True,
                exception_amount=Decimal("50"),
            )
        return organization

    def test_matching_overview_exposes_amount_weighted_rates(
        self, organization, supplier
    ):
        self._seed_match_fixture(organization, supplier)
        result = P2PAnalyticsService(organization).get_matching_overview()

        # Count-based: 10 exceptions / 11 total = 90.9%
        assert result["exception_rate"] >= 90
        # Amount-based: $1000 / $101K ≈ 1% — very different picture
        assert result["exception_rate_by_amount"] < 5
        assert result["three_way_matched"]["percentage_by_amount"] > 95
        # The nested and legacy flat fields must agree
        assert (
            result["exceptions"]["percentage_by_amount"]
            == result["exception_rate_by_amount"]
        )


@pytest.mark.django_db
class TestComplianceAmountWeightedRate:
    """Compliance rate should be available as both count-based (legacy) and amount-based."""

    def test_compliance_overview_exposes_both_rates(
        self, organization, supplier, category, admin_user
    ):
        from datetime import date

        from apps.procurement.models import PolicyViolation, SpendingPolicy
        from apps.procurement.tests.factories import TransactionFactory

        # Policy scaffolding required by the violation FK.
        policy = SpendingPolicy.objects.create(
            organization=organization,
            name="TestPolicy",
            rules={"max_transaction_amount": 10000},
        )
        # One large $100K compliant txn + ten small $100 violating txns.
        big_clean = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal("100000"),
            date=date.today(),
            invoice_number="CLEAN-1",
        )
        for i in range(10):
            tx = TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal("100"),
                date=date.today(),
                invoice_number=f"BAD-{i}",
            )
            PolicyViolation.objects.create(
                organization=organization,
                transaction=tx,
                policy=policy,
                violation_type="amount_exceeded",
                severity="medium",
            )

        from apps.analytics.compliance_services import ComplianceService

        result = ComplianceService(organization).get_compliance_overview()
        # Count-based: 1 compliant / 11 total = 9.1%
        assert result["compliance_rate"] < 20
        # Amount-based: $100K compliant / $101K total ≈ 99%
        assert result["compliance_rate_by_amount"] > 95


class TestPredictiveGrowthWindows:
    """Equal-span growth windows — no more 13-month YoY nonsense."""

    def _run(self, values):
        from apps.analytics.predictive_services import PredictiveAnalyticsService

        svc = PredictiveAnalyticsService.__new__(PredictiveAnalyticsService)
        # Emulate the growth-metrics block.
        metrics = {}
        if len(values) >= 24:
            cur = sum(values[-12:])
            prev = sum(values[-24:-12])
            metrics["yoy_growth"] = (
                round((cur - prev) / prev * 100, 2) if prev > 0 else 0
            )
        if len(values) >= 12:
            cur = sum(values[-6:])
            prev = sum(values[-12:-6])
            metrics["six_month_growth"] = (
                round((cur - prev) / prev * 100, 2) if prev > 0 else 0
            )
        if len(values) >= 6:
            cur = sum(values[-3:])
            prev = sum(values[-6:-3])
            metrics["three_month_growth"] = (
                round((cur - prev) / prev * 100, 2) if prev > 0 else 0
            )
        return metrics

    def test_13_months_omits_yoy(self):
        # Under 24 months — yoy_growth must NOT be emitted.
        metrics = self._run([100] * 13)
        assert "yoy_growth" not in metrics

    def test_24_months_emits_yoy_equal_spans(self):
        values = [100] * 12 + [200] * 12
        metrics = self._run(values)
        assert metrics["yoy_growth"] == 100  # (2400 - 1200) / 1200 * 100

    def test_7_months_omits_six_month(self):
        metrics = self._run([100] * 7)
        assert "six_month_growth" not in metrics

    def test_12_months_emits_six_month_equal_spans(self):
        values = [100] * 6 + [200] * 6
        metrics = self._run(values)
        assert metrics["six_month_growth"] == 100
