"""
Tests for YearOverYearAnalyticsService — Cluster 5 scope.
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.analytics.services import AnalyticsService
from apps.analytics.services.yoy import _yoy_change
from apps.procurement.tests.factories import (
    TransactionFactory, SupplierFactory, CategoryFactory,
)


class TestYoyChangeHelper:
    """New / discontinued / standard-delta semantics for the shared helper."""

    def test_standard_delta(self):
        change, is_new, is_discontinued = _yoy_change(100, 200)
        assert change == 100
        assert not is_new and not is_discontinued

    def test_new_category_flagged(self):
        change, is_new, is_discontinued = _yoy_change(0, 500)
        assert is_new is True
        assert is_discontinued is False
        # Numeric change_pct is kept at 100 for back-compat; UI should render via the flag.
        assert change == 100

    def test_discontinued_flagged(self):
        change, is_new, is_discontinued = _yoy_change(500, 0)
        assert is_discontinued is True
        assert is_new is False
        assert change == -100

    def test_both_zero(self):
        change, is_new, is_discontinued = _yoy_change(0, 0)
        assert change == 0
        assert not is_new and not is_discontinued

    def test_decline(self):
        change, _, _ = _yoy_change(1000, 750)
        assert change == -25


@pytest.mark.django_db
class TestYoyDetailedAccuracy:
    """Real-data invariants the Cluster 5 pass added."""

    def _seed_two_years(self, organization, admin_user):
        cat_legacy = CategoryFactory(organization=organization, name='Legacy')
        cat_new = CategoryFactory(organization=organization, name='NewCat')
        supplier = SupplierFactory(organization=organization)
        # Legacy: present in both years (FY2024 = Jul 2023-Jun 2024, FY2025 = Jul 2024-Jun 2025)
        for d in [date(2023, 10, 15), date(2024, 10, 15)]:
            TransactionFactory(
                organization=organization, supplier=supplier, category=cat_legacy,
                uploaded_by=admin_user, amount=Decimal('1000'), date=d,
                invoice_number=f'LEG-{d.isoformat()}',
            )
        # NewCat: only present in FY2025
        TransactionFactory(
            organization=organization, supplier=supplier, category=cat_new,
            uploaded_by=admin_user, amount=Decimal('500'), date=date(2024, 10, 20),
            invoice_number='NEW-1',
        )

    def test_new_category_has_is_new_flag(self, organization, admin_user):
        self._seed_two_years(organization, admin_user)
        result = AnalyticsService(organization).get_detailed_year_over_year(use_fiscal_year=True)
        new_cat = next(c for c in result['category_comparison'] if c['category'] == 'NewCat')
        assert new_cat['is_new'] is True
        assert new_cat['is_discontinued'] is False
        legacy = next(c for c in result['category_comparison'] if c['category'] == 'Legacy')
        assert legacy['is_new'] is False

    def test_single_year_flagged_as_insufficient(self, organization, supplier, category, admin_user):
        TransactionFactory(
            organization=organization, supplier=supplier, category=category,
            uploaded_by=admin_user, amount=Decimal('500'), date=date(2024, 6, 15),
            invoice_number='SOLO-1',
        )
        result = AnalyticsService(organization).get_detailed_year_over_year(use_fiscal_year=True)
        assert result['summary']['insufficient_data_for_yoy'] is True

    def test_calendar_year_uses_calendar_month_labels(self, organization, admin_user):
        self._seed_two_years(organization, admin_user)
        fy_result = AnalyticsService(organization).get_detailed_year_over_year(use_fiscal_year=True)
        cy_result = AnalyticsService(organization).get_detailed_year_over_year(use_fiscal_year=False)
        # Fiscal labels are Jul-first; calendar labels are Jan-first.
        assert fy_result['monthly_comparison'][0]['month'] == 'Jul'
        assert cy_result['monthly_comparison'][0]['month'] == 'Jan'

    def test_top_gainers_exclude_new_categories(self, organization, admin_user):
        # Gainers rank change_pct; including new categories would put the
        # placeholder 100% at the top and hide real YoY gainers.
        self._seed_two_years(organization, admin_user)
        result = AnalyticsService(organization).get_detailed_year_over_year(use_fiscal_year=True)
        gainer_names = [g['category'] for g in result['top_gainers']]
        assert 'NewCat' not in gainer_names
