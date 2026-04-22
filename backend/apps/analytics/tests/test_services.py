"""
Tests for analytics services.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from apps.analytics.services import AnalyticsService
from apps.analytics.services.base import BaseAnalyticsService
from apps.procurement.models import Transaction, Supplier, Category
from apps.procurement.tests.factories import (
    TransactionFactory, SupplierFactory, CategoryFactory
)


@pytest.mark.django_db
class TestBaseFilterValidation:
    """Filter values that would otherwise fail silently or crash mid-query."""

    def test_inverted_date_range_raises(self, organization):
        with pytest.raises(ValueError, match='date_from'):
            AnalyticsService(organization, filters={
                'date_from': '2024-12-31',
                'date_to': '2024-01-01',
            })

    def test_equal_date_range_is_allowed(self, organization):
        AnalyticsService(organization, filters={
            'date_from': '2024-06-15',
            'date_to': '2024-06-15',
        })

    def test_non_numeric_min_amount_raises(self, organization):
        with pytest.raises(ValueError, match='min_amount'):
            AnalyticsService(organization, filters={'min_amount': 'abc'})

    def test_non_numeric_max_amount_raises(self, organization):
        with pytest.raises(ValueError, match='max_amount'):
            AnalyticsService(organization, filters={'max_amount': 'xyz'})

    def test_string_numeric_amounts_are_accepted(self, organization):
        AnalyticsService(organization, filters={
            'min_amount': '100.50',
            'max_amount': '1000',
        })

    def test_empty_string_amount_is_ignored(self, organization):
        AnalyticsService(organization, filters={'min_amount': '', 'max_amount': ''})


class TestFiscalYearMonthHelpers:
    """Boundary-case tests for the Jul-Jun fiscal calendar helpers."""

    @pytest.fixture
    def svc(self):
        return BaseAnalyticsService.__new__(BaseAnalyticsService)

    @pytest.mark.parametrize('input_date,expected_fy', [
        (date(2024, 6, 30), 2024),   # last day of FY2024
        (date(2024, 7, 1), 2025),    # first day of FY2025
        (date(2024, 12, 31), 2025),  # mid-FY2025
        (date(2025, 1, 1), 2025),    # calendar-year boundary within FY2025
        (date(2025, 6, 30), 2025),   # last day of FY2025
    ])
    def test_fiscal_year_boundaries(self, svc, input_date, expected_fy):
        assert svc._get_fiscal_year(input_date) == expected_fy

    def test_fiscal_year_calendar_mode(self, svc):
        assert svc._get_fiscal_year(date(2024, 12, 15), use_fiscal_year=False) == 2024
        assert svc._get_fiscal_year(date(2024, 7, 1), use_fiscal_year=False) == 2024

    @pytest.mark.parametrize('input_date,expected_fm', [
        (date(2024, 7, 1), 1),    # Jul = FM1
        (date(2024, 12, 1), 6),   # Dec = FM6
        (date(2025, 1, 1), 7),    # Jan = FM7
        (date(2025, 6, 30), 12),  # Jun = FM12
    ])
    def test_fiscal_month_boundaries(self, svc, input_date, expected_fm):
        assert svc._get_fiscal_month(input_date) == expected_fm

    def test_fiscal_month_calendar_mode(self, svc):
        for m in range(1, 13):
            assert svc._get_fiscal_month(date(2024, m, 15), use_fiscal_year=False) == m


@pytest.mark.django_db
class TestAnalyticsServiceOverview:
    """Tests for overview statistics."""

    def test_get_overview_stats_with_data(self, organization, multiple_transactions):
        """Test overview stats with transaction data."""
        service = AnalyticsService(organization)
        stats = service.get_overview_stats()

        assert stats['total_spend'] > 0
        assert stats['transaction_count'] == len(multiple_transactions)
        assert stats['supplier_count'] >= 1
        assert stats['category_count'] >= 1
        assert stats['avg_transaction'] > 0

    def test_get_overview_stats_empty(self, organization):
        """Test overview stats with no data."""
        service = AnalyticsService(organization)
        stats = service.get_overview_stats()

        assert stats['total_spend'] == 0
        assert stats['transaction_count'] == 0
        assert stats['supplier_count'] == 0
        assert stats['category_count'] == 0
        assert stats['avg_transaction'] == 0

    def test_overview_stats_organization_scoped(self, organization, other_organization, admin_user, other_org_user):
        """Test that stats are scoped to organization."""
        # Create transactions in both organizations
        supplier1 = SupplierFactory(organization=organization)
        category1 = CategoryFactory(organization=organization)
        TransactionFactory(
            organization=organization,
            supplier=supplier1,
            category=category1,
            uploaded_by=admin_user,
            amount=Decimal('1000.00'),
            invoice_number='ORG-1'
        )

        supplier2 = SupplierFactory(organization=other_organization)
        category2 = CategoryFactory(organization=other_organization)
        TransactionFactory(
            organization=other_organization,
            supplier=supplier2,
            category=category2,
            uploaded_by=other_org_user,
            amount=Decimal('5000.00')
        )

        service = AnalyticsService(organization)
        stats = service.get_overview_stats()

        assert stats['total_spend'] == 1000.0
        assert stats['transaction_count'] == 1


@pytest.mark.django_db
class TestSpendByCategory:
    """Tests for spend by category analysis."""

    def test_spend_by_category(self, organization, supplier, admin_user):
        """Test spend breakdown by category."""
        category1 = CategoryFactory(organization=organization, name='Category A')
        category2 = CategoryFactory(organization=organization, name='Category B')

        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category1,
            uploaded_by=admin_user,
            amount=Decimal('1000.00'),
            invoice_number='CAT-A-1'
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category1,
            uploaded_by=admin_user,
            amount=Decimal('500.00'),
            invoice_number='CAT-A-2'
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category2,
            uploaded_by=admin_user,
            amount=Decimal('2000.00'),
            invoice_number='CAT-B-1'
        )

        service = AnalyticsService(organization)
        result = service.get_spend_by_category()

        assert len(result) == 2
        # Should be ordered by total descending
        assert result[0]['category'] == 'Category B'
        assert result[0]['amount'] == 2000.0
        assert result[1]['category'] == 'Category A'
        assert result[1]['amount'] == 1500.0

    def test_spend_by_category_empty(self, organization):
        """Test spend by category with no data."""
        service = AnalyticsService(organization)
        result = service.get_spend_by_category()
        assert result == []


@pytest.mark.django_db
class TestSpendBySupplier:
    """Tests for spend by supplier analysis."""

    def test_spend_by_supplier(self, organization, category, admin_user):
        """Test spend breakdown by supplier."""
        supplier1 = SupplierFactory(organization=organization, name='Supplier A')
        supplier2 = SupplierFactory(organization=organization, name='Supplier B')

        TransactionFactory(
            organization=organization,
            supplier=supplier1,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('3000.00'),
            invoice_number='SUP-A-1'
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier2,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('1000.00'),
            invoice_number='SUP-B-1'
        )

        service = AnalyticsService(organization)
        result = service.get_spend_by_supplier()

        assert len(result) == 2
        assert result[0]['supplier'] == 'Supplier A'
        assert result[0]['amount'] == 3000.0


@pytest.mark.django_db
class TestMonthlyTrend:
    """Tests for monthly trend analysis."""

    def test_monthly_trend(self, organization, supplier, category, admin_user):
        """Test monthly spend trend."""
        base_date = date.today()

        # Create transactions across months
        for i in range(6):
            tx_date = base_date - timedelta(days=i * 30)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(1000 + i * 100)),
                date=tx_date,
                invoice_number=f'MONTH-{i}'
            )

        service = AnalyticsService(organization)
        result = service.get_monthly_trend(months=12)

        assert len(result) >= 1
        for item in result:
            assert 'month' in item
            assert 'amount' in item
            assert 'count' in item

    def test_monthly_trend_respects_months_parameter(self, organization, supplier, category, admin_user):
        """Test that months parameter limits the range."""
        # Create a transaction 13 months ago
        old_date = date.today() - timedelta(days=400)
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            date=old_date,
            invoice_number='OLD-1'
        )

        service = AnalyticsService(organization)
        result = service.get_monthly_trend(months=12)

        # Old transaction should not be included
        for item in result:
            month_date = item['month']
            assert month_date >= (date.today() - timedelta(days=365)).strftime('%Y-%m')


@pytest.mark.django_db
class TestParetoAnalysis:
    """Tests for Pareto (80/20) analysis."""

    def test_pareto_analysis(self, organization, category, admin_user):
        """Test Pareto analysis with cumulative percentages."""
        # Create suppliers with different spend levels
        supplier_large = SupplierFactory(organization=organization, name='Large Supplier')
        supplier_medium = SupplierFactory(organization=organization, name='Medium Supplier')
        supplier_small = SupplierFactory(organization=organization, name='Small Supplier')

        TransactionFactory(
            organization=organization,
            supplier=supplier_large,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('10000.00'),
            invoice_number='PARETO-1'
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier_medium,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('3000.00'),
            invoice_number='PARETO-2'
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier_small,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('1000.00'),
            invoice_number='PARETO-3'
        )

        service = AnalyticsService(organization)
        result = service.get_pareto_analysis()

        assert len(result) == 3
        # Should be sorted by amount descending
        assert result[0]['supplier'] == 'Large Supplier'
        # Cumulative percentage should increase
        assert result[0]['cumulative_percentage'] < result[1]['cumulative_percentage']
        assert result[2]['cumulative_percentage'] == 100.0


@pytest.mark.django_db
class TestTailSpendAnalysis:
    """Tests for tail spend analysis."""

    def test_tail_spend_analysis(self, organization, category, admin_user):
        """Test tail spend identification."""
        # Create suppliers with varying spend
        for i in range(10):
            supplier = SupplierFactory(organization=organization, name=f'Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str((i + 1) * 1000)),
                invoice_number=f'TAIL-{i}'
            )

        service = AnalyticsService(organization)
        result = service.get_tail_spend_analysis(threshold_percentage=20)

        assert 'tail_suppliers' in result
        assert 'tail_count' in result
        assert 'tail_spend' in result
        assert 'tail_percentage' in result
        # Tail percentage may exceed threshold due to granularity (whole suppliers)
        assert result['tail_percentage'] <= 30  # Allow for granularity


@pytest.mark.django_db
class TestSpendStratification:
    """Tests for spend stratification (Kraljic matrix)."""

    def test_spend_stratification(self, organization, admin_user):
        """Test strategic/leverage/bottleneck/tactical classification."""
        # Create categories with different characteristics
        for i in range(4):
            category = CategoryFactory(organization=organization, name=f'Category {i}')
            num_suppliers = (i % 2) + 1  # 1 or 2 suppliers

            for j in range(num_suppliers):
                supplier = SupplierFactory(organization=organization, name=f'Cat{i}-Sup{j}')
                amount = Decimal(str(1000 * (i + 1)))  # Varying spend levels
                TransactionFactory(
                    organization=organization,
                    supplier=supplier,
                    category=category,
                    uploaded_by=admin_user,
                    amount=amount,
                    invoice_number=f'STRAT-{i}-{j}'
                )

        service = AnalyticsService(organization)
        result = service.get_spend_stratification()

        assert 'strategic' in result
        assert 'leverage' in result
        assert 'bottleneck' in result
        assert 'tactical' in result

        # Total categories should equal sum of all quadrants
        total = (len(result['strategic']) + len(result['leverage']) +
                 len(result['bottleneck']) + len(result['tactical']))
        assert total == 4


@pytest.mark.django_db
class TestSeasonalityAnalysis:
    """Tests for seasonality analysis."""

    def test_seasonality_analysis(self, organization, supplier, category, admin_user):
        """Test monthly seasonality patterns."""
        # Create transactions across different months
        for month in [1, 3, 6, 12]:
            tx_date = date(2024, month, 15)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(month * 1000)),
                date=tx_date,
                invoice_number=f'SEASON-{month}'
            )

        service = AnalyticsService(organization)
        result = service.get_seasonality_analysis()

        # Should have 12 months
        assert len(result) == 12
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for i, item in enumerate(result):
            assert item['month'] == month_names[i]
            assert 'average_spend' in item
            assert 'occurrences' in item


@pytest.mark.django_db
class TestSeasonalityOrdering:
    """Regression tests for category_seasonality sort order.

    Frontend reads category_seasonality[0] and [-1] to render the
    "Highest Seasonality" and "Lowest Seasonality" cards. The backend
    must sort by seasonality_strength descending. Sorting by any other
    key (e.g., savings_potential) reintroduces the bug.
    """

    FISCAL_MONTH_DATES = [
        (2023, 7), (2023, 8), (2023, 9), (2023, 10), (2023, 11), (2023, 12),
        (2024, 1), (2024, 2), (2024, 3), (2024, 4), (2024, 5), (2024, 6),
    ]

    def _seed_monthly(self, organization, category, supplier, admin_user, fiscal_monthly_amounts):
        for idx, amount in enumerate(fiscal_monthly_amounts):
            if amount <= 0:
                continue
            year, month = self.FISCAL_MONTH_DATES[idx]
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(amount)),
                date=date(year, month, 15),
                invoice_number=f'{category.name}-M{idx:02d}',
            )

    def test_sort_by_seasonality_strength_not_savings(self, organization, supplier, admin_user):
        # BigMild: $4.8M total, strength ~= 20.4% (> 15 filter, but lowest of the three)
        cat_big_mild = CategoryFactory(organization=organization, name='BigMild')
        self._seed_monthly(
            organization, cat_big_mild, supplier, admin_user,
            [300000, 300000, 300000, 300000, 500000, 500000,
             500000, 500000, 400000, 400000, 400000, 400000],
        )

        # SmallExtreme: ~$100K total, one-month spike, strength ~= 292%
        cat_small_extreme = CategoryFactory(organization=organization, name='SmallExtreme')
        self._seed_monthly(
            organization, cat_small_extreme, supplier, admin_user,
            [90000, 1000, 1000, 1000, 1000, 1000,
             1000, 1000, 1000, 1000, 1000, 0],
        )

        # MidModerate: $570K total, arithmetic ramp, strength ~= 36%
        cat_mid_moderate = CategoryFactory(organization=organization, name='MidModerate')
        self._seed_monthly(
            organization, cat_mid_moderate, supplier, admin_user,
            [20000, 25000, 30000, 35000, 40000, 45000,
             50000, 55000, 60000, 65000, 70000, 75000],
        )

        result = AnalyticsService(organization).get_detailed_seasonality_analysis(use_fiscal_year=True)
        category_seasonality = result['category_seasonality']

        names = [c['category'] for c in category_seasonality]
        assert set(names) == {'BigMild', 'SmallExtreme', 'MidModerate'}

        assert category_seasonality[0]['category'] == 'SmallExtreme'
        assert category_seasonality[-1]['category'] == 'BigMild'

        by_savings = sorted(category_seasonality, key=lambda c: c['savings_potential'], reverse=True)
        assert by_savings[0]['category'] == 'BigMild'
        assert category_seasonality[0]['category'] != by_savings[0]['category']

        strengths = [c['seasonality_strength'] for c in category_seasonality]
        assert strengths == sorted(strengths, reverse=True)


@pytest.mark.django_db
class TestYearOverYearComparison:
    """Tests for year-over-year comparison."""

    def test_year_over_year(self, organization, supplier, category, admin_user):
        """Test YoY comparison with growth calculation."""
        # Create transactions in different years
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('10000.00'),
            date=date(2023, 6, 15),
            invoice_number='YOY-2023'
        )
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('15000.00'),
            date=date(2024, 6, 15),
            invoice_number='YOY-2024'
        )

        service = AnalyticsService(organization)
        result = service.get_year_over_year_comparison()

        assert len(result) == 2
        assert result[0]['year'] == 2023
        assert result[1]['year'] == 2024

        # Second year should have growth percentage
        if 'growth_percentage' in result[1]:
            assert result[1]['growth_percentage'] == 50.0  # 50% growth


@pytest.mark.django_db
class TestSupplierConsolidation:
    """Tests for supplier consolidation opportunities."""

    def test_consolidation_opportunities(self, organization, admin_user):
        """Test identification of consolidation opportunities."""
        category = CategoryFactory(organization=organization, name='Consolidate Category')

        # Create multiple suppliers in same category
        for i in range(5):
            supplier = SupplierFactory(organization=organization, name=f'Consolidate Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str((i + 1) * 500)),
                invoice_number=f'CONS-{i}'
            )

        service = AnalyticsService(organization)
        result = service.get_supplier_consolidation_opportunities()

        # Should find the category with 5 suppliers
        assert len(result) >= 1
        opportunity = result[0]
        assert opportunity['supplier_count'] > 2
        assert 'potential_savings' in opportunity
        assert opportunity['potential_savings'] > 0

    def test_no_consolidation_with_few_suppliers(self, organization, supplier, category, admin_user):
        """Test that categories with few suppliers are not flagged."""
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            invoice_number='NO-CONS-1'
        )

        service = AnalyticsService(organization)
        result = service.get_supplier_consolidation_opportunities()

        # Category with only one supplier should not be flagged
        category_names = [o['category'] for o in result]
        assert category.name not in category_names


@pytest.mark.django_db
class TestAnalyticsServiceEmpty:
    """Tests for analytics service with empty data."""

    def test_pareto_empty(self, organization):
        """Test Pareto analysis with no data."""
        service = AnalyticsService(organization)
        result = service.get_pareto_analysis()
        assert result == []

    def test_tail_spend_empty(self, organization):
        """Test tail spend with no data."""
        service = AnalyticsService(organization)
        result = service.get_tail_spend_analysis()
        assert result['tail_suppliers'] == []
        assert result['tail_count'] == 0
        assert result['tail_spend'] == 0

    def test_stratification_empty(self, organization):
        """Test stratification with no data."""
        service = AnalyticsService(organization)
        result = service.get_spend_stratification()
        assert len(result['strategic']) == 0
        assert len(result['leverage']) == 0
        assert len(result['bottleneck']) == 0
        assert len(result['tactical']) == 0

    def test_seasonality_empty(self, organization):
        """Test seasonality with no data."""
        service = AnalyticsService(organization)
        result = service.get_seasonality_analysis()
        assert len(result) == 12
        for item in result:
            assert item['average_spend'] == 0

    def test_yoy_empty(self, organization):
        """Test YoY with no data."""
        service = AnalyticsService(organization)
        result = service.get_year_over_year_comparison()
        assert result == []

    def test_consolidation_empty(self, organization):
        """Test consolidation with no data."""
        service = AnalyticsService(organization)
        result = service.get_supplier_consolidation_opportunities()
        assert result == []
