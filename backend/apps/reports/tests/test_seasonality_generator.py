"""
Tests for SeasonalityReportGenerator.

Verifies that the generator's savings_opportunities list remains sorted by
savings_potential regardless of the underlying service sort, and that
category_analysis reflects the service's strength-descending ordering.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.procurement.tests.factories import (
    CategoryFactory,
    SupplierFactory,
    TransactionFactory,
)
from apps.reports.generators.seasonality import SeasonalityReportGenerator

FISCAL_MONTH_DATES = [
    (2023, 7),
    (2023, 8),
    (2023, 9),
    (2023, 10),
    (2023, 11),
    (2023, 12),
    (2024, 1),
    (2024, 2),
    (2024, 3),
    (2024, 4),
    (2024, 5),
    (2024, 6),
]


def _seed_monthly(organization, category, supplier, admin_user, fiscal_monthly_amounts):
    for idx, amount in enumerate(fiscal_monthly_amounts):
        if amount <= 0:
            continue
        year, month = FISCAL_MONTH_DATES[idx]
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal(str(amount)),
            date=date(year, month, 15),
            invoice_number=f"{category.name}-M{idx:02d}",
        )


@pytest.mark.django_db
class TestSeasonalityGeneratorParity:
    """
    Fixture produces three categories where savings_potential ordering
    differs from seasonality_strength ordering:

        Category       Strength    Savings
        BigMild        ~20%        ~$100K  (biggest savings)
        SmallExtreme   ~292%       ~$22K
        MidModerate    ~36%        ~$19K
    """

    def _build_fixture(self, organization, admin_user):
        supplier = SupplierFactory(organization=organization)

        big_mild = CategoryFactory(organization=organization, name="BigMild")
        _seed_monthly(
            organization,
            big_mild,
            supplier,
            admin_user,
            [
                300000,
                300000,
                300000,
                300000,
                500000,
                500000,
                500000,
                500000,
                400000,
                400000,
                400000,
                400000,
            ],
        )

        small_extreme = CategoryFactory(organization=organization, name="SmallExtreme")
        _seed_monthly(
            organization,
            small_extreme,
            supplier,
            admin_user,
            [90000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 0],
        )

        mid_moderate = CategoryFactory(organization=organization, name="MidModerate")
        _seed_monthly(
            organization,
            mid_moderate,
            supplier,
            admin_user,
            [
                20000,
                25000,
                30000,
                35000,
                40000,
                45000,
                50000,
                55000,
                60000,
                65000,
                70000,
                75000,
            ],
        )

    def test_savings_opportunities_sorted_by_savings_descending(
        self, organization, admin_user
    ):
        self._build_fixture(organization, admin_user)

        result = SeasonalityReportGenerator(organization).generate()
        opportunities = result["savings_opportunities"]

        assert len(opportunities) >= 3
        savings_values = [o["savings_potential"] for o in opportunities]
        assert savings_values == sorted(savings_values, reverse=True)

        assert opportunities[0]["category"] == "BigMild"

    def test_category_analysis_reflects_strength_descending_service_order(
        self, organization, admin_user
    ):
        self._build_fixture(organization, admin_user)

        result = SeasonalityReportGenerator(organization).generate()
        category_analysis = result["category_analysis"]

        names = [c["category"] for c in category_analysis]
        assert names[:3] == ["SmallExtreme", "MidModerate", "BigMild"]

        strengths = [c["seasonality_strength"] for c in category_analysis]
        assert strengths == sorted(strengths, reverse=True)

    def test_two_sort_orders_are_independent(self, organization, admin_user):
        """The savings-opportunities list must not drift if the service sort changes."""
        self._build_fixture(organization, admin_user)

        result = SeasonalityReportGenerator(organization).generate()

        category_analysis_lead = result["category_analysis"][0]["category"]
        savings_opportunities_lead = result["savings_opportunities"][0]["category"]

        assert category_analysis_lead == "SmallExtreme"
        assert savings_opportunities_lead == "BigMild"
        assert category_analysis_lead != savings_opportunities_lead
