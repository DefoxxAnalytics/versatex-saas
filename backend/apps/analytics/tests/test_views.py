"""
Tests for analytics views.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from apps.procurement.tests.factories import TransactionFactory, SupplierFactory, CategoryFactory


@pytest.mark.django_db
class TestOverviewStats:
    """Tests for overview stats endpoint."""

    def test_overview_stats(self, authenticated_client, transaction):
        """Test getting overview statistics."""
        url = reverse('overview-stats')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'total_spend' in response.data
        assert 'transaction_count' in response.data
        assert 'supplier_count' in response.data
        assert 'category_count' in response.data

    def test_overview_stats_unauthorized(self, api_client):
        """Test that unauthenticated users cannot access stats."""
        url = reverse('overview-stats')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSpendByCategory:
    """Tests for spend by category endpoint."""

    def test_spend_by_category(self, authenticated_client, transaction):
        """Test getting spend by category."""
        url = reverse('spend-by-category')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_spend_by_category_organization_scoped(self, authenticated_client, other_organization, other_org_user):
        """Test that results are scoped to user's organization."""
        # Create transaction in other org
        other_supplier = SupplierFactory(organization=other_organization)
        other_category = CategoryFactory(organization=other_organization, name='Other Org Category')
        TransactionFactory(
            organization=other_organization,
            supplier=other_supplier,
            category=other_category,
            uploaded_by=other_org_user
        )

        url = reverse('spend-by-category')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        category_names = [item['category'] for item in response.data]
        assert 'Other Org Category' not in category_names


@pytest.mark.django_db
class TestSpendBySupplier:
    """Tests for spend by supplier endpoint."""

    def test_spend_by_supplier(self, authenticated_client, transaction):
        """Test getting spend by supplier."""
        url = reverse('spend-by-supplier')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
class TestMonthlyTrend:
    """Tests for monthly trend endpoint."""

    def test_monthly_trend_default(self, authenticated_client, transaction):
        """Test getting monthly trend with default parameters."""
        url = reverse('monthly-trend')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_monthly_trend_custom_months(self, authenticated_client, transaction):
        """Test getting monthly trend with custom months parameter."""
        url = reverse('monthly-trend')
        response = authenticated_client.get(url, {'months': 6})
        assert response.status_code == status.HTTP_200_OK

    def test_monthly_trend_invalid_months(self, authenticated_client):
        """Test that invalid months parameter returns error."""
        url = reverse('monthly-trend')
        response = authenticated_client.get(url, {'months': 'invalid'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_monthly_trend_months_out_of_range(self, authenticated_client):
        """Test that months out of range returns error."""
        url = reverse('monthly-trend')
        response = authenticated_client.get(url, {'months': 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        response = authenticated_client.get(url, {'months': 200})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestParetoAnalysis:
    """Tests for Pareto analysis endpoint."""

    def test_pareto_analysis(self, authenticated_client, transaction):
        """Test getting Pareto analysis."""
        url = reverse('pareto-analysis')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

        if response.data:
            assert 'supplier' in response.data[0]
            assert 'cumulative_percentage' in response.data[0]


@pytest.mark.django_db
class TestTailSpendAnalysis:
    """Tests for tail spend analysis endpoint."""

    def test_tail_spend_default(self, authenticated_client, transaction):
        """Test getting tail spend with default threshold."""
        url = reverse('tail-spend')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'tail_suppliers' in response.data
        assert 'tail_percentage' in response.data

    def test_tail_spend_custom_threshold(self, authenticated_client, transaction):
        """Test getting tail spend with custom threshold."""
        url = reverse('tail-spend')
        response = authenticated_client.get(url, {'threshold': 10})
        assert response.status_code == status.HTTP_200_OK

    def test_tail_spend_invalid_threshold(self, authenticated_client):
        """Test that invalid threshold returns error."""
        url = reverse('tail-spend')
        response = authenticated_client.get(url, {'threshold': 'abc'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_tail_spend_threshold_out_of_range(self, authenticated_client):
        """Test that threshold out of range returns error."""
        url = reverse('tail-spend')
        response = authenticated_client.get(url, {'threshold': 150})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSpendStratification:
    """Tests for spend stratification endpoint."""

    def test_spend_stratification(self, authenticated_client, transaction):
        """Test getting spend stratification."""
        url = reverse('stratification')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'strategic' in response.data
        assert 'leverage' in response.data
        assert 'bottleneck' in response.data
        assert 'tactical' in response.data


@pytest.mark.django_db
class TestSeasonalityAnalysis:
    """Tests for seasonality analysis endpoint."""

    def test_seasonality_analysis(self, authenticated_client, transaction):
        """Test getting seasonality analysis."""
        url = reverse('seasonality')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 12  # 12 months


@pytest.mark.django_db
class TestYearOverYear:
    """Tests for year over year comparison endpoint."""

    def test_year_over_year(self, authenticated_client, transaction):
        """Test getting year over year comparison."""
        url = reverse('year-over-year')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
class TestConsolidationOpportunities:
    """Tests for consolidation opportunities endpoint."""

    def test_consolidation_opportunities(self, authenticated_client, organization, admin_user, category):
        """Test getting consolidation opportunities."""
        # Create multiple suppliers for a category
        for i in range(4):
            supplier = SupplierFactory(organization=organization, name=f'Consol Supplier {i}')
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                invoice_number=f'CONSOL-VIEW-{i}'
            )

        url = reverse('consolidation')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
class TestAnalyticsAuthentication:
    """Tests for authentication on analytics endpoints."""

    def test_all_endpoints_require_auth(self, api_client):
        """Test that all analytics endpoints require authentication."""
        endpoints = [
            'overview-stats',
            'spend-by-category',
            'spend-by-supplier',
            'monthly-trend',
            'pareto-analysis',
            'tail-spend',
            'stratification',
            'seasonality',
            'year-over-year',
            'consolidation',
        ]

        for endpoint in endpoints:
            url = reverse(endpoint)
            response = api_client.get(url)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"Endpoint {endpoint} did not require authentication"


@pytest.mark.django_db
class TestAnalyticsValidation:
    """Tests for parameter validation on analytics endpoints."""

    def test_validate_int_param_valid(self, authenticated_client):
        """Test that valid integer parameters are accepted."""
        url = reverse('monthly-trend')
        response = authenticated_client.get(url, {'months': 24})
        assert response.status_code == status.HTTP_200_OK

    def test_validate_int_param_boundary(self, authenticated_client):
        """Test boundary values for parameters."""
        url = reverse('monthly-trend')

        # Min boundary
        response = authenticated_client.get(url, {'months': 1})
        assert response.status_code == status.HTTP_200_OK

        # Max boundary
        response = authenticated_client.get(url, {'months': 120})
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAnalyticsOrganizationScoping:
    """Tests for organization scoping across all analytics endpoints."""

    def test_overview_scoped(self, authenticated_client, organization, other_organization, admin_user, other_org_user):
        """Test that overview stats are scoped to user's org."""
        supplier = SupplierFactory(organization=organization)
        category = CategoryFactory(organization=organization)
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            invoice_number='SCOPE-1'
        )

        other_supplier = SupplierFactory(organization=other_organization)
        other_category = CategoryFactory(organization=other_organization)
        TransactionFactory(
            organization=other_organization,
            supplier=other_supplier,
            category=other_category,
            uploaded_by=other_org_user
        )

        url = reverse('overview-stats')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Should only see 1 transaction from own org
        assert response.data['transaction_count'] == 1
