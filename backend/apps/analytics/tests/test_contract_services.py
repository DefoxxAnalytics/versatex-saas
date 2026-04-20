"""
Tests for Contract Analytics service.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from apps.analytics.contract_services import ContractAnalyticsService
from apps.procurement.models import Contract
from apps.procurement.tests.factories import (
    TransactionFactory, SupplierFactory, CategoryFactory
)


@pytest.fixture
def contract_factory(organization, supplier):
    """Factory function for creating contracts."""
    def create_contract(**kwargs):
        defaults = {
            'organization': organization,
            'supplier': supplier,
            'contract_number': f'CNT-{Contract.objects.count() + 1:04d}',
            'title': 'Test Contract',
            'total_value': Decimal('100000.00'),
            'annual_value': Decimal('50000.00'),
            'start_date': date.today() - timedelta(days=180),
            'end_date': date.today() + timedelta(days=180),
            'status': 'active',
            'renewal_notice_days': 90,
            'auto_renew': False,
        }
        defaults.update(kwargs)
        return Contract.objects.create(**defaults)
    return create_contract


@pytest.mark.django_db
class TestContractAnalyticsServiceInitialization:
    """Tests for ContractAnalyticsService initialization."""

    def test_initialization(self, organization):
        """Test service initialization."""
        service = ContractAnalyticsService(organization)
        assert service.organization == organization


@pytest.mark.django_db
class TestContractOverview:
    """Tests for contract overview statistics."""

    def test_overview_with_contracts(self, organization, supplier, category, admin_user, contract_factory):
        """Test contract overview with data."""
        # Create active contracts
        contract_factory(status='active')
        contract_factory(
            contract_number='CNT-0002',
            status='active',
            end_date=date.today() + timedelta(days=30)  # Expiring soon
        )

        # Create transactions for contracted supplier
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('5000.00'),
                invoice_number=f'CTR-OV-{i}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_contract_overview()

        assert result['total_contracts'] == 2
        assert result['active_contracts'] == 2
        assert result['expiring_soon'] >= 1
        assert result['total_value'] > 0
        assert 'contract_coverage_percentage' in result

    def test_overview_empty(self, organization):
        """Test contract overview with no data."""
        service = ContractAnalyticsService(organization)
        result = service.get_contract_overview()

        assert result['total_contracts'] == 0
        assert result['active_contracts'] == 0
        assert result['total_value'] == 0.0

    def test_overview_contract_coverage(self, organization, supplier, category, admin_user, contract_factory):
        """Test contract coverage calculation."""
        # Create contract
        contract_factory()

        # Create transactions - some with contracted supplier, some without
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'COVERED-{i}'
            )

        non_contracted = SupplierFactory(organization=organization, name='Non-Contracted')
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=non_contracted,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'UNCOVERED-{i}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_contract_overview()

        # Should be 50% coverage (5 contracted, 5 not)
        assert 40 <= result['contract_coverage_percentage'] <= 60


@pytest.mark.django_db
class TestContractsList:
    """Tests for contracts list retrieval."""

    def test_contracts_list(self, organization, supplier, contract_factory):
        """Test getting list of contracts."""
        contract_factory(title='Contract A')
        contract_factory(contract_number='CNT-0002', title='Contract B')

        service = ContractAnalyticsService(organization)
        result = service.get_contracts_list()

        assert len(result) == 2
        for contract in result:
            assert 'id' in contract
            assert 'uuid' in contract
            assert 'title' in contract
            assert 'supplier_name' in contract
            assert 'days_to_expiry' in contract

    def test_contracts_list_empty(self, organization):
        """Test contracts list with no data."""
        service = ContractAnalyticsService(organization)
        result = service.get_contracts_list()

        assert result == []

    def test_contracts_list_days_to_expiry(self, organization, supplier, contract_factory):
        """Test that days to expiry is calculated correctly."""
        future_date = date.today() + timedelta(days=100)
        contract_factory(end_date=future_date)

        service = ContractAnalyticsService(organization)
        result = service.get_contracts_list()

        assert len(result) == 1
        assert 95 <= result[0]['days_to_expiry'] <= 105


@pytest.mark.django_db
class TestContractDetail:
    """Tests for contract detail retrieval."""

    def test_contract_detail_found(self, organization, supplier, category, admin_user, contract_factory):
        """Test getting contract detail."""
        contract = contract_factory(title='Detail Contract')

        # Create transactions for contract supplier
        for i in range(3):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=date.today() - timedelta(days=i * 30),
                invoice_number=f'DETAIL-{i}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_contract_detail(contract.id)

        assert result['title'] == 'Detail Contract'
        assert 'performance' in result
        assert result['performance']['actual_spend'] == 30000.0
        assert 'utilization_percentage' in result['performance']

    def test_contract_detail_not_found(self, organization):
        """Test contract detail for non-existent contract."""
        service = ContractAnalyticsService(organization)
        result = service.get_contract_detail(99999)

        assert 'error' in result

    def test_contract_detail_utilization(self, organization, supplier, category, admin_user, contract_factory):
        """Test utilization calculation."""
        contract = contract_factory(total_value=Decimal('100000.00'))

        # Spend 50% of contract value
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=date.today() - timedelta(days=i * 10),
                invoice_number=f'UTIL-{i}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_contract_detail(contract.id)

        assert 45 <= result['performance']['utilization_percentage'] <= 55


@pytest.mark.django_db
class TestExpiringContracts:
    """Tests for expiring contracts retrieval."""

    def test_expiring_contracts_found(self, organization, supplier, contract_factory):
        """Test finding contracts expiring soon."""
        # Contract expiring in 30 days
        contract_factory(
            title='Expiring Soon',
            end_date=date.today() + timedelta(days=30)
        )

        # Contract not expiring soon
        contract_factory(
            contract_number='CNT-0002',
            title='Not Expiring',
            end_date=date.today() + timedelta(days=200)
        )

        service = ContractAnalyticsService(organization)
        result = service.get_expiring_contracts(days=90)

        assert len(result) == 1
        assert result[0]['title'] == 'Expiring Soon'
        assert 'recommendation' in result[0]
        assert 'priority' in result[0]

    def test_expiring_contracts_empty(self, organization, supplier, contract_factory):
        """Test no expiring contracts."""
        contract_factory(end_date=date.today() + timedelta(days=365))

        service = ContractAnalyticsService(organization)
        result = service.get_expiring_contracts(days=90)

        assert len(result) == 0

    def test_expiring_contracts_within_notice_period(self, organization, supplier, contract_factory):
        """Test contracts within renewal notice period."""
        contract_factory(
            title='Notice Period',
            end_date=date.today() + timedelta(days=60),
            renewal_notice_days=90
        )

        service = ContractAnalyticsService(organization)
        result = service.get_expiring_contracts()

        assert len(result) == 1
        assert result[0]['within_notice_period'] is True


@pytest.mark.django_db
class TestContractPerformance:
    """Tests for contract performance metrics."""

    def test_performance_metrics(self, organization, supplier, category, admin_user, contract_factory):
        """Test performance metrics calculation."""
        contract = contract_factory(total_value=Decimal('120000.00'))

        # Create monthly transactions
        for month in range(6):
            tx_date = date.today() - timedelta(days=month * 30)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=tx_date,
                invoice_number=f'PERF-{month}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_contract_performance(contract.id)

        assert result['total_spend'] == 60000.0
        assert result['transaction_count'] == 6
        assert 'monthly_breakdown' in result
        assert 'variance' in result

    def test_performance_not_found(self, organization):
        """Test performance for non-existent contract."""
        service = ContractAnalyticsService(organization)
        result = service.get_contract_performance(99999)

        assert 'error' in result


@pytest.mark.django_db
class TestSavingsOpportunities:
    """Tests for savings opportunities identification."""

    def test_underutilized_contract(self, organization, supplier, category, admin_user, contract_factory):
        """Test finding underutilized contracts."""
        # Contract with low utilization (starts 180 days ago, ends 180 days from now)
        contract_factory(
            title='Underutilized',
            total_value=Decimal('100000.00'),
            start_date=date.today() - timedelta(days=180),
            end_date=date.today() + timedelta(days=180)
        )

        # Create minimal spend (well below expected)
        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('5000.00'),
            date=date.today() - timedelta(days=30),
            invoice_number='LOW-SPEND'
        )

        service = ContractAnalyticsService(organization)
        result = service.get_savings_opportunities()

        underutilized = [o for o in result if o['type'] == 'underutilized_contract']
        assert len(underutilized) >= 1

    def test_off_contract_spend(self, organization, supplier, category, admin_user, contract_factory):
        """Test finding off-contract spending opportunities."""
        contract_factory()

        # Create significant spend with non-contracted supplier
        non_contracted = SupplierFactory(organization=organization, name='Off-Contract Supplier')
        for i in range(10):
            TransactionFactory(
                organization=organization,
                supplier=non_contracted,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('5000.00'),
                date=date.today() - timedelta(days=i * 10),
                invoice_number=f'OFF-{i}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_savings_opportunities()

        off_contract = [o for o in result if o['type'] == 'off_contract_spend']
        assert len(off_contract) >= 1

    def test_savings_empty(self, organization):
        """Test savings with no data."""
        service = ContractAnalyticsService(organization)
        result = service.get_savings_opportunities()

        assert isinstance(result, list)


@pytest.mark.django_db
class TestRenewalRecommendations:
    """Tests for renewal recommendations."""

    def test_renewal_recommendations(self, organization, supplier, category, admin_user, contract_factory):
        """Test generating renewal recommendations."""
        contract = contract_factory(
            title='Renewing Contract',
            end_date=date.today() + timedelta(days=60),
            total_value=Decimal('100000.00')
        )

        # Create transactions showing high utilization
        for i in range(10):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=date.today() - timedelta(days=i * 10),
                invoice_number=f'RENEW-{i}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_renewal_recommendations()

        assert len(result) >= 1
        assert 'action' in result[0]
        assert 'recommendation' in result[0]
        assert 'priority' in result[0]
        assert 'suggested_new_value' in result[0]

    def test_renewal_high_utilization(self, organization, supplier, category, admin_user, contract_factory):
        """Test renewal recommendation for high utilization contract."""
        contract = contract_factory(
            title='High Util Contract',
            end_date=date.today() + timedelta(days=60),
            total_value=Decimal('50000.00')
        )

        # Spend exceeding contract value
        for i in range(10):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=date.today() - timedelta(days=i * 10),
                invoice_number=f'HIGH-UTIL-{i}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_renewal_recommendations()

        high_util = [r for r in result if r['title'] == 'High Util Contract']
        if high_util:
            assert high_util[0]['action'] in ['renew_increase', 'renew_same']


@pytest.mark.django_db
class TestContractVsActualSpend:
    """Tests for contract vs actual spend comparison."""

    def test_comparison_on_track(self, organization, supplier, category, admin_user, contract_factory):
        """Test comparison when spend is on track."""
        contract = contract_factory(total_value=Decimal('120000.00'))

        # Create appropriate spend
        for month in range(6):
            tx_date = date.today() - timedelta(days=month * 30)
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('8000.00'),
                date=tx_date,
                invoice_number=f'TRACK-{month}'
            )

        service = ContractAnalyticsService(organization)
        result = service.get_contract_vs_actual_spend()

        assert len(result) >= 1
        assert 'variance' in result[0]
        assert 'variance_percentage' in result[0]
        assert 'status' in result[0]

    def test_comparison_specific_contract(self, organization, supplier, category, admin_user, contract_factory):
        """Test comparison for specific contract."""
        contract = contract_factory()

        TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('10000.00'),
            invoice_number='SPECIFIC-1'
        )

        service = ContractAnalyticsService(organization)
        result = service.get_contract_vs_actual_spend(contract_id=contract.id)

        assert len(result) == 1
        assert result[0]['contract_id'] == contract.id


@pytest.mark.django_db
class TestOrganizationScoping:
    """Tests for organization data isolation."""

    def test_contracts_scoped_to_organization(
        self, organization, other_organization, supplier, admin_user, other_org_user, contract_factory
    ):
        """Test that contracts are scoped to organization."""
        # Create contract in main organization
        contract_factory(title='Main Org Contract')

        # Create contract in other organization
        other_supplier = SupplierFactory(organization=other_organization)
        Contract.objects.create(
            organization=other_organization,
            supplier=other_supplier,
            contract_number='OTHER-001',
            title='Other Org Contract',
            total_value=Decimal('100000.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            status='active'
        )

        service = ContractAnalyticsService(organization)
        result = service.get_contracts_list()

        # Should only see main org contract
        assert len(result) == 1
        assert result[0]['title'] == 'Main Org Contract'
