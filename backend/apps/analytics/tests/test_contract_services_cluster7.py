"""
Contract analytics regression tests — Cluster 7 scope.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.analytics.contract_services import ContractAnalyticsService
from apps.procurement.models import Contract
from apps.procurement.tests.factories import (
    CategoryFactory,
    SupplierFactory,
    TransactionFactory,
)


@pytest.fixture
def supplier_with_history(organization, supplier, category, admin_user):
    """Seed 2 years of pre-contract spend + 3 months under a new contract."""
    today = date.today()
    # Pre-contract history ($600K over 24 months, ~$25K/month) dated more than
    # 100 days ago so it's outside the contract window.
    for m in range(24):
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal("25000"),
            date=today - timedelta(days=30 * (m + 4) + 15),
            invoice_number=f"HIST-{m}",
        )
    # 3 months under a new $500K contract (~$20K/month → utilization ≈ 12%).
    for m in range(3):
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal("20000"),
            date=today - timedelta(days=30 * m + 5),
            invoice_number=f"CONTRACT-{m}",
        )

    contract = Contract.objects.create(
        organization=organization,
        supplier=supplier,
        contract_number="CON-CLUSTER7",
        title="Test Contract",
        total_value=Decimal("500000"),
        start_date=today - timedelta(days=100),
        end_date=today + timedelta(days=265),
        status="active",
    )
    contract.categories.add(category)
    return contract


@pytest.mark.django_db
class TestContractsListUtilization:
    """Utilization must scope to the contract's own date window."""

    def test_utilization_excludes_pre_contract_history(
        self, organization, supplier_with_history
    ):
        service = ContractAnalyticsService(organization)
        contracts = service.get_contracts_list()
        assert len(contracts) == 1
        utilization = contracts[0]["utilization_percentage"]
        # 3 months × $20K = $60K against $500K contract → 12%.
        assert 10 < utilization < 15, f"expected ~12%, got {utilization}"
        # Prior bug: $600K pre-contract + $60K within-contract → 132% utilization.
        assert utilization < 100


@pytest.mark.django_db
class TestContractCoverageWindow:
    """Coverage % must reflect recent spend, not pre-contract history."""

    def test_coverage_scoped_to_trailing_year(self, organization, category, admin_user):
        today = date.today()
        # $4.8M of spend from 1+ year ago under no contract.
        old_supplier = SupplierFactory(organization=organization, name="OldSupplier")
        for m in range(24):
            TransactionFactory(
                organization=organization,
                supplier=old_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal("200000"),
                date=today - timedelta(days=30 * (m + 13) + 15),
                invoice_number=f"OLD-{m}",
            )
        # $120K of recent spend from a different supplier WITH an active contract.
        contracted_supplier = SupplierFactory(
            organization=organization, name="ContractedSupplier"
        )
        for m in range(6):
            TransactionFactory(
                organization=organization,
                supplier=contracted_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal("20000"),
                date=today - timedelta(days=30 * m + 5),
                invoice_number=f"NEW-{m}",
            )
        Contract.objects.create(
            organization=organization,
            supplier=contracted_supplier,
            contract_number="CON-NEW",
            title="New",
            total_value=Decimal("500000"),
            start_date=today - timedelta(days=180),
            end_date=today + timedelta(days=185),
            status="active",
        )

        overview = ContractAnalyticsService(organization).get_contract_overview()
        # Trailing-12-month spend: only the recent $120K is in the window and
        # all of it is from a contracted supplier → coverage = 100%.
        assert overview["contract_coverage_percentage"] == 100.0
        assert overview["contract_coverage_window_days"] == 365


@pytest.mark.django_db
class TestContractPerformanceMonthlyAverage:
    """actual_monthly must use full duration, not months-with-activity count."""

    def test_sporadic_spend_does_not_inflate_monthly_average(
        self, organization, supplier, category, admin_user
    ):
        today = date.today()
        contract = Contract.objects.create(
            organization=organization,
            supplier=supplier,
            contract_number="CON-SPORADIC",
            title="Sporadic",
            total_value=Decimal("120000"),  # expected $10K/mo over 12 months
            start_date=today - timedelta(days=365),
            end_date=today,
            status="active",
        )
        contract.categories.add(category)
        # Only $30K spend total, concentrated in 3 months.
        for m in [0, 4, 8]:
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal("10000"),
                date=today - timedelta(days=30 * m + 15),
                invoice_number=f"SPOR-{m}",
            )

        perf = ContractAnalyticsService(organization).get_contract_performance(
            contract.id
        )
        # Expected ~$10K/month; actual_monthly divided by full duration is
        # ~$30K / 13 months = ~$2.3K. Previously the denominator was 3 (months
        # with activity) which gave $10K — misleadingly "on target."
        assert perf["expected_monthly_spend"] > 8000
        assert perf["actual_monthly_spend"] < 3500
        assert perf["variance"] < -5000
        assert perf["active_spend_months"] == 3
