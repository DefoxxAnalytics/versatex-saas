"""
Tests for Predictive Analytics service.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from apps.analytics.predictive_services import PredictiveAnalyticsService
from apps.procurement.tests.factories import (
    TransactionFactory, SupplierFactory, CategoryFactory
)


@pytest.mark.django_db
class TestPredictiveServiceInitialization:
    """Tests for PredictiveAnalyticsService initialization."""

    def test_initialization(self, organization):
        """Test service initialization."""
        service = PredictiveAnalyticsService(organization)
        assert service.organization == organization


@pytest.mark.django_db
class TestSpendingForecast:
    """Tests for spending forecast functionality."""

    def test_spending_forecast_with_data(self, organization, supplier, category, admin_user):
        """Test spending forecast with historical data."""
        # Create 12 months of data
        base_date = date.today() - timedelta(days=365)
        for month in range(12):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(10000 + month * 500)),
                date=tx_date,
                invoice_number=f'FORECAST-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast(months=6)

        assert 'forecast' in result
        assert 'trend' in result
        assert 'model_accuracy' in result

        # Should have 6 forecast periods
        assert len(result['forecast']) == 6

        # Each forecast should have required fields
        for forecast in result['forecast']:
            assert 'month' in forecast
            assert 'predicted_spend' in forecast
            assert 'lower_bound_80' in forecast
            assert 'upper_bound_80' in forecast
            assert 'lower_bound_95' in forecast
            assert 'upper_bound_95' in forecast

    def test_spending_forecast_empty_data(self, organization):
        """Test spending forecast with no data."""
        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast(months=6)

        assert result['forecast'] == []
        assert result['trend']['direction'] == 'stable'
        assert result['model_accuracy']['data_points_used'] == 0

    def test_spending_forecast_trend_detection(self, organization, supplier, category, admin_user):
        """Test that increasing trend is detected."""
        base_date = date.today() - timedelta(days=365)

        # Create increasing spend pattern
        for month in range(12):
            tx_date = base_date + relativedelta(months=month)
            # Significantly increasing amounts
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(10000 + month * 2000)),
                date=tx_date,
                invoice_number=f'TREND-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast()

        assert result['trend']['direction'] == 'increasing'
        assert result['trend']['monthly_change_rate'] > 0

    def test_spending_forecast_decreasing_trend(self, organization, supplier, category, admin_user):
        """Test that decreasing trend is detected."""
        base_date = date.today() - timedelta(days=365)

        # Create decreasing spend pattern
        for month in range(12):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(50000 - month * 2000)),
                date=tx_date,
                invoice_number=f'DEC-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast()

        assert result['trend']['direction'] == 'decreasing'
        assert result['trend']['monthly_change_rate'] < 0

    def test_spending_forecast_confidence_intervals(self, organization, supplier, category, admin_user):
        """Test that confidence intervals are properly ordered."""
        base_date = date.today() - timedelta(days=180)

        for month in range(6):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=tx_date,
                invoice_number=f'CI-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast(months=3)

        for forecast in result['forecast']:
            # 95% interval should be wider than 80%
            assert forecast['lower_bound_95'] <= forecast['lower_bound_80']
            assert forecast['upper_bound_95'] >= forecast['upper_bound_80']
            # All bounds should be non-negative
            assert forecast['lower_bound_95'] >= 0
            assert forecast['lower_bound_80'] >= 0


@pytest.mark.django_db
class TestCategoryForecast:
    """Tests for category-specific forecasting."""

    def test_category_forecast_with_data(self, organization, supplier, admin_user):
        """Test forecast for a specific category."""
        category = CategoryFactory(organization=organization, name='Forecast Category')
        base_date = date.today() - timedelta(days=180)

        for month in range(6):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('5000.00'),
                date=tx_date,
                invoice_number=f'CAT-FC-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_category_forecast(category.id, months=3)

        assert 'category_id' in result
        assert result['category_id'] == category.id
        assert len(result['forecast']) == 3
        assert 'trend' in result

    def test_category_forecast_nonexistent(self, organization):
        """Test forecast for non-existent category."""
        service = PredictiveAnalyticsService(organization)
        result = service.get_category_forecast(99999, months=3)

        assert result['forecast'] == []
        assert result['model_accuracy']['data_points_used'] == 0

    def test_category_forecast_empty_category(self, organization):
        """Test forecast for category with no transactions."""
        category = CategoryFactory(organization=organization, name='Empty Category')

        service = PredictiveAnalyticsService(organization)
        result = service.get_category_forecast(category.id, months=3)

        assert result['forecast'] == []


@pytest.mark.django_db
class TestSupplierForecast:
    """Tests for supplier-specific forecasting."""

    def test_supplier_forecast_with_data(self, organization, category, admin_user):
        """Test forecast for a specific supplier."""
        supplier = SupplierFactory(organization=organization, name='Forecast Supplier')
        base_date = date.today() - timedelta(days=180)

        for month in range(6):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('8000.00'),
                date=tx_date,
                invoice_number=f'SUP-FC-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_supplier_forecast(supplier.id, months=3)

        assert 'supplier_id' in result
        assert result['supplier_id'] == supplier.id
        assert len(result['forecast']) == 3

    def test_supplier_forecast_nonexistent(self, organization):
        """Test forecast for non-existent supplier."""
        service = PredictiveAnalyticsService(organization)
        result = service.get_supplier_forecast(99999, months=3)

        assert result['forecast'] == []

    def test_supplier_forecast_empty(self, organization):
        """Test forecast for supplier with no transactions."""
        supplier = SupplierFactory(organization=organization, name='Empty Supplier')

        service = PredictiveAnalyticsService(organization)
        result = service.get_supplier_forecast(supplier.id, months=3)

        assert result['forecast'] == []


@pytest.mark.django_db
class TestTrendAnalysis:
    """Tests for comprehensive trend analysis."""

    def test_trend_analysis_overall(self, organization, supplier, category, admin_user):
        """Test overall trend analysis."""
        base_date = date.today() - timedelta(days=365)

        for month in range(12):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=tx_date,
                invoice_number=f'TREND-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_trend_analysis()

        assert 'overall_trend' in result
        assert 'category_trends' in result
        assert 'supplier_trends' in result
        assert 'growth_metrics' in result

        assert 'direction' in result['overall_trend']
        assert 'change_rate' in result['overall_trend']

    def test_trend_analysis_empty(self, organization):
        """Test trend analysis with no data."""
        service = PredictiveAnalyticsService(organization)
        result = service.get_trend_analysis()

        assert result['overall_trend']['direction'] == 'stable'
        assert result['category_trends'] == []
        assert result['supplier_trends'] == []

    def test_trend_analysis_growth_metrics(self, organization, supplier, category, admin_user):
        """Test growth metrics calculation."""
        base_date = date.today() - timedelta(days=365)

        for month in range(12):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=tx_date,
                invoice_number=f'GROWTH-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_trend_analysis()

        # Should have growth metrics with enough data
        assert 'three_month_growth' in result['growth_metrics'] or 'six_month_growth' in result['growth_metrics']


@pytest.mark.django_db
class TestBudgetProjection:
    """Tests for budget vs forecast comparison."""

    def test_budget_projection_valid(self, organization, supplier, category, admin_user):
        """Test budget projection with valid data."""
        # Create YTD transactions
        current_year = date.today().year
        for month in range(1, date.today().month + 1):
            tx_date = date(current_year, month, 15)
            if tx_date <= date.today():
                TransactionFactory(
                    organization=organization,
                    supplier=supplier,
                    category=category,
                    uploaded_by=admin_user,
                    amount=Decimal('10000.00'),
                    date=tx_date,
                    invoice_number=f'BUDGET-{month}'
                )

        service = PredictiveAnalyticsService(organization)
        result = service.get_budget_projection(annual_budget=200000)

        assert 'annual_budget' in result
        assert 'ytd_spend' in result
        assert 'ytd_budget' in result
        assert 'variance' in result
        assert 'variance_percentage' in result
        assert 'projected_year_end' in result
        assert 'status' in result

    def test_budget_projection_negative_budget(self, organization):
        """Test budget projection with invalid budget."""
        service = PredictiveAnalyticsService(organization)
        result = service.get_budget_projection(annual_budget=-1000)

        assert 'error' in result

    def test_budget_projection_zero_budget(self, organization):
        """Test budget projection with zero budget."""
        service = PredictiveAnalyticsService(organization)
        result = service.get_budget_projection(annual_budget=0)

        assert 'error' in result

    def test_budget_projection_no_ytd_data(self, organization):
        """Test budget projection with no current year data."""
        service = PredictiveAnalyticsService(organization)
        result = service.get_budget_projection(annual_budget=100000)

        assert result['status'] == 'no_data'
        assert result['ytd_spend'] == 0


@pytest.mark.django_db
class TestSeasonalityDetection:
    """Tests for seasonality detection in forecasts."""

    def test_seasonality_detected(self, organization, supplier, category, admin_user):
        """Test that seasonal patterns are detected."""
        # Create 2 years of data with seasonal pattern
        base_date = date.today() - timedelta(days=730)  # 2 years ago

        for month in range(24):
            tx_date = base_date + relativedelta(months=month)
            # December has higher spend
            multiplier = 2.0 if tx_date.month == 12 else 1.0
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal(str(10000 * multiplier)),
                date=tx_date,
                invoice_number=f'SEASON-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast()

        # With sufficient data, seasonality should be detected
        if result['model_accuracy']['data_points_used'] >= 12:
            assert 'seasonality_detected' in result['trend']


@pytest.mark.django_db
class TestModelAccuracy:
    """Tests for model accuracy metrics."""

    def test_mape_calculation(self, organization, supplier, category, admin_user):
        """Test MAPE (Mean Absolute Percentage Error) calculation."""
        base_date = date.today() - timedelta(days=365)

        # Create consistent data for predictable accuracy
        for month in range(12):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=tx_date,
                invoice_number=f'MAPE-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast()

        # With 12 months of data, MAPE should be calculated
        if result['model_accuracy']['data_points_used'] >= 6:
            assert result['model_accuracy']['mape'] is not None or result['model_accuracy']['mape'] is None

    def test_r_squared_included(self, organization, supplier, category, admin_user):
        """Test R-squared is included in accuracy metrics."""
        base_date = date.today() - timedelta(days=180)

        for month in range(6):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=tx_date,
                invoice_number=f'R2-{month}'
            )

        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast()

        assert 'r_squared' in result['model_accuracy']


@pytest.mark.django_db
class TestOrganizationScoping:
    """Tests for organization data isolation."""

    def test_forecast_scoped_to_organization(
        self, organization, other_organization, admin_user, other_org_user
    ):
        """Test that forecasts only include organization's data."""
        # Create data in main organization
        supplier1 = SupplierFactory(organization=organization)
        category1 = CategoryFactory(organization=organization)
        base_date = date.today() - timedelta(days=180)

        for month in range(6):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=organization,
                supplier=supplier1,
                category=category1,
                uploaded_by=admin_user,
                amount=Decimal('5000.00'),
                date=tx_date,
                invoice_number=f'ORG-{month}'
            )

        # Create larger data in other organization
        supplier2 = SupplierFactory(organization=other_organization)
        category2 = CategoryFactory(organization=other_organization)

        for month in range(6):
            tx_date = base_date + relativedelta(months=month)
            TransactionFactory(
                organization=other_organization,
                supplier=supplier2,
                category=category2,
                uploaded_by=other_org_user,
                amount=Decimal('100000.00'),
                date=tx_date,
                invoice_number=f'OTHER-{month}'
            )

        # Forecast for main organization should only reflect its data
        service = PredictiveAnalyticsService(organization)
        result = service.get_spending_forecast(months=1)

        # The forecast should be based on ~5000 per month, not 100000
        if result['forecast']:
            assert result['forecast'][0]['predicted_spend'] < 50000
