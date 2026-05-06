"""
Phase 5 Task 5.10 — equal-span guard for the simple YoY endpoint.

Accuracy convention §4 (docs/CLAUDE.md, root): YoY growth percentages must be
emitted only when both comparison windows are equal-and-full. The simple
``get_year_over_year_comparison`` endpoint previously divided a full year by a
partial prior year, producing the same ~1100% anomaly we already fixed in the
Predictive growth-metrics block (Finding B8 cousin). This test pins the new
behaviour:

- Partial-year vs partial-year (or partial vs full) → ``growth_percentage``
  omitted, ``insufficient_data_for_growth`` set.
- Two full calendar years → ``growth_percentage`` present and accurate.
- Single year → no growth on the only row (existing behaviour preserved).
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.analytics.services.yoy import YearOverYearAnalyticsService
from apps.procurement.tests.factories import (
    CategoryFactory, SupplierFactory, TransactionFactory,
)


def _seed_year(organization, supplier, category, admin_user, year, months, amount=Decimal('1000')):
    """Seed one transaction in each of the given calendar months for ``year``."""
    for month in months:
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=amount,
            date=date(year, month, 15),
            invoice_number=f'INV-{year}-{month:02d}',
        )


@pytest.mark.django_db
class TestYoyEqualSpanGuard:
    """Equal-span guard on get_year_over_year_comparison (simple endpoint)."""

    def test_partial_years_omits_growth_percentage(self, organization, admin_user):
        """Year A: 3 months, Year B: 12 months → growth must NOT be emitted."""
        supplier = SupplierFactory(organization=organization)
        category = CategoryFactory(organization=organization)

        _seed_year(organization, supplier, category, admin_user,
                   year=2024, months=[10, 11, 12])
        _seed_year(organization, supplier, category, admin_user,
                   year=2025, months=list(range(1, 13)))

        result = YearOverYearAnalyticsService(organization).get_year_over_year_comparison()

        assert len(result) == 2
        year_2025 = next(r for r in result if r['year'] == 2025)
        assert 'growth_percentage' not in year_2025, (
            'Equal-span guard should omit growth_percentage when prior year '
            'has only partial coverage (3 of 12 months).'
        )
        assert year_2025.get('insufficient_data_for_growth') is True

    def test_two_full_years_emits_growth_percentage(self, organization, admin_user):
        """Both years have all 12 months → growth_percentage is emitted and accurate."""
        supplier = SupplierFactory(organization=organization)
        category = CategoryFactory(organization=organization)

        _seed_year(organization, supplier, category, admin_user,
                   year=2024, months=list(range(1, 13)), amount=Decimal('1000'))
        _seed_year(organization, supplier, category, admin_user,
                   year=2025, months=list(range(1, 13)), amount=Decimal('2000'))

        result = YearOverYearAnalyticsService(organization).get_year_over_year_comparison()

        assert len(result) == 2
        year_2025 = next(r for r in result if r['year'] == 2025)
        assert 'growth_percentage' in year_2025
        # 12 * 2000 vs 12 * 1000 = +100%
        assert year_2025['growth_percentage'] == 100.0
        assert 'insufficient_data_for_growth' not in year_2025

    def test_single_year_no_growth_on_first_row(self, organization, admin_user):
        """Only one year of data → first row has neither growth nor insufficient flag."""
        supplier = SupplierFactory(organization=organization)
        category = CategoryFactory(organization=organization)

        _seed_year(organization, supplier, category, admin_user,
                   year=2025, months=list(range(1, 13)))

        result = YearOverYearAnalyticsService(organization).get_year_over_year_comparison()

        assert len(result) == 1
        only_row = result[0]
        assert only_row['year'] == 2025
        assert 'growth_percentage' not in only_row
        assert 'insufficient_data_for_growth' not in only_row
