"""
Tests for Compliance and Maverick Spend service.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from apps.analytics.compliance_services import ComplianceService
from apps.procurement.models import Contract, SpendingPolicy, PolicyViolation
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


@pytest.fixture
def policy_factory(organization):
    """Factory function for creating spending policies."""
    def create_policy(**kwargs):
        defaults = {
            'organization': organization,
            'name': f'Policy {SpendingPolicy.objects.count() + 1}',
            'description': 'Test policy',
            'rules': {},
            'is_active': True,
        }
        defaults.update(kwargs)
        return SpendingPolicy.objects.create(**defaults)
    return create_policy


@pytest.fixture
def violation_factory(organization, policy_factory):
    """Factory function for creating policy violations."""
    def create_violation(transaction, **kwargs):
        policy = kwargs.pop('policy', None) or policy_factory()
        defaults = {
            'organization': organization,
            'transaction': transaction,
            'policy': policy,
            'violation_type': 'amount_exceeded',
            'severity': 'medium',
            'details': {},
            'is_resolved': False,
        }
        defaults.update(kwargs)
        return PolicyViolation.objects.create(**defaults)
    return create_violation


@pytest.mark.django_db
class TestComplianceServiceInitialization:
    """Tests for ComplianceService initialization."""

    def test_initialization(self, organization):
        """Test service initialization."""
        service = ComplianceService(organization)
        assert service.organization == organization


@pytest.mark.django_db
class TestComplianceOverview:
    """Tests for compliance overview statistics."""

    def test_overview_basic(self, organization, supplier, category, admin_user, contract_factory):
        """Test basic compliance overview."""
        # Create contract
        contract_factory()

        # Create transactions
        for i in range(10):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'COMP-OV-{i}'
            )

        service = ComplianceService(organization)
        result = service.get_compliance_overview()

        assert 'total_transactions' in result
        assert 'total_spend' in result
        assert 'compliance_rate' in result
        assert 'total_violations' in result
        assert 'maverick_spend' in result
        assert 'maverick_percentage' in result

    def test_overview_with_violations(
        self, organization, supplier, category, admin_user, violation_factory
    ):
        """Test overview with violations."""
        # Create transactions and violations
        for i in range(5):
            tx = TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'VIOL-{i}'
            )
            if i < 2:  # Create violations for 2 transactions
                violation_factory(tx, severity='high')

        service = ComplianceService(organization)
        result = service.get_compliance_overview()

        assert result['total_violations'] == 2
        assert result['severity_breakdown']['high'] == 2
        # Compliance rate should be 60% (3 of 5 transactions without violations)
        assert 55 <= result['compliance_rate'] <= 65

    def test_overview_empty(self, organization):
        """Test overview with no data."""
        service = ComplianceService(organization)
        result = service.get_compliance_overview()

        assert result['total_transactions'] == 0
        assert result['compliance_rate'] == 100
        assert result['maverick_percentage'] == 0

    def test_overview_maverick_spend(
        self, organization, supplier, category, admin_user, contract_factory
    ):
        """Test maverick spend calculation."""
        # Create contract for one supplier
        contract_factory()

        # Create transactions with contracted supplier
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'ON-CONTRACT-{i}'
            )

        # Create transactions with non-contracted supplier
        off_contract_supplier = SupplierFactory(organization=organization, name='Off-Contract')
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=off_contract_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'OFF-CONTRACT-{i}'
            )

        service = ComplianceService(organization)
        result = service.get_compliance_overview()

        # 50% should be maverick spend
        assert 45 <= result['maverick_percentage'] <= 55


@pytest.mark.django_db
class TestMaverickSpendAnalysis:
    """Tests for maverick spend analysis."""

    def test_maverick_analysis_with_contracts(
        self, organization, supplier, category, admin_user, contract_factory
    ):
        """Test maverick spend analysis with active contracts."""
        contract_factory()

        # On-contract spend
        for i in range(5):
            TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('5000.00'),
                invoice_number=f'ON-{i}'
            )

        # Off-contract spend
        maverick_supplier = SupplierFactory(organization=organization, name='Maverick Supplier')
        for i in range(3):
            TransactionFactory(
                organization=organization,
                supplier=maverick_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('5000.00'),
                invoice_number=f'MAVERICK-{i}'
            )

        service = ComplianceService(organization)
        result = service.get_maverick_spend_analysis()

        assert 'total_maverick_spend' in result
        assert 'maverick_suppliers' in result
        assert 'maverick_percentage' in result
        assert 'recommendations' in result

        # Should have maverick supplier
        maverick_names = [s['supplier_name'] for s in result['maverick_suppliers']]
        assert 'Maverick Supplier' in maverick_names

    def test_maverick_recommendations(
        self, organization, supplier, category, admin_user
    ):
        """Test maverick spend recommendations."""
        # Create significant off-contract spend
        maverick = SupplierFactory(organization=organization, name='High Spend Maverick')
        for i in range(10):
            TransactionFactory(
                organization=organization,
                supplier=maverick,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'HIGH-MAV-{i}'
            )

        service = ComplianceService(organization)
        result = service.get_maverick_spend_analysis()

        assert len(result['recommendations']) > 0
        # Should recommend contract negotiation for high spend
        rec_types = [r['type'] for r in result['recommendations']]
        assert 'contract_negotiation' in rec_types or 'spend_consolidation' in rec_types

    def test_maverick_analysis_empty(self, organization):
        """Test maverick analysis with no data."""
        service = ComplianceService(organization)
        result = service.get_maverick_spend_analysis()

        assert result['total_maverick_spend'] == 0
        assert result['maverick_percentage'] == 0


@pytest.mark.django_db
class TestPolicyViolations:
    """Tests for policy violations retrieval."""

    def test_get_violations(
        self, organization, supplier, category, admin_user, violation_factory
    ):
        """Test getting policy violations."""
        tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('15000.00'),
            invoice_number='VIOL-TEST'
        )
        violation_factory(tx, severity='high', violation_type='amount_exceeded')

        service = ComplianceService(organization)
        result = service.get_policy_violations()

        assert len(result) == 1
        assert result[0]['severity'] == 'high'
        assert result[0]['violation_type'] == 'amount_exceeded'
        assert 'transaction_id' in result[0]
        assert 'supplier_name' in result[0]

    def test_get_violations_filter_resolved(
        self, organization, supplier, category, admin_user, violation_factory
    ):
        """Test filtering violations by resolved status."""
        for i in range(3):
            tx = TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                invoice_number=f'RES-{i}'
            )
            violation_factory(tx, is_resolved=(i < 2))

        service = ComplianceService(organization)

        unresolved = service.get_policy_violations(resolved=False)
        assert len(unresolved) == 1

        resolved = service.get_policy_violations(resolved=True)
        assert len(resolved) == 2

    def test_get_violations_filter_severity(
        self, organization, supplier, category, admin_user, violation_factory
    ):
        """Test filtering violations by severity."""
        for severity in ['critical', 'high', 'medium', 'low']:
            tx = TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('5000.00'),
                invoice_number=f'SEV-{severity}'
            )
            violation_factory(tx, severity=severity)

        service = ComplianceService(organization)
        critical = service.get_policy_violations(severity='critical')

        assert len(critical) == 1
        assert critical[0]['severity'] == 'critical'

    def test_violations_empty(self, organization):
        """Test getting violations with no data."""
        service = ComplianceService(organization)
        result = service.get_policy_violations()

        assert result == []


@pytest.mark.django_db
class TestViolationTrends:
    """Tests for violation trend analysis."""

    def test_violation_trends(
        self, organization, supplier, category, admin_user, violation_factory
    ):
        """Test violation trend analysis."""
        # Create violations across multiple months
        for month_offset in range(3):
            tx = TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('10000.00'),
                date=date.today() - timedelta(days=month_offset * 30),
                invoice_number=f'TREND-{month_offset}'
            )
            violation_factory(tx, severity='high')

        service = ComplianceService(organization)
        result = service.get_violation_trends(months=6)

        assert 'monthly_trend' in result
        assert 'by_type' in result
        assert len(result['monthly_trend']) > 0

    def test_violation_trends_empty(self, organization):
        """Test trends with no violations."""
        service = ComplianceService(organization)
        result = service.get_violation_trends(months=6)

        assert result['monthly_trend'] == []
        assert result['by_type']['amount_exceeded'] == 0


@pytest.mark.django_db
class TestEvaluateTransaction:
    """Tests for transaction policy evaluation."""

    def test_evaluate_amount_exceeded(
        self, organization, supplier, category, admin_user, policy_factory
    ):
        """Test detecting amount exceeded violation."""
        policy_factory(
            name='Amount Limit Policy',
            rules={'max_transaction_amount': 5000}
        )

        tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('10000.00'),
            invoice_number='EXCEED-AMOUNT'
        )

        service = ComplianceService(organization)
        violations = service.evaluate_transaction(tx.id)

        assert len(violations) >= 1
        amount_violations = [v for v in violations if v['violation_type'] == 'amount_exceeded']
        assert len(amount_violations) == 1

    def test_evaluate_no_contract(
        self, organization, supplier, category, admin_user, policy_factory
    ):
        """Test detecting no contract violation."""
        policy_factory(
            name='Contract Required Policy',
            rules={'require_contract': True}
        )

        tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('5000.00'),
            invoice_number='NO-CONTRACT'
        )

        service = ComplianceService(organization)
        violations = service.evaluate_transaction(tx.id)

        contract_violations = [v for v in violations if v['violation_type'] == 'no_contract']
        assert len(contract_violations) == 1

    def test_evaluate_nonexistent_transaction(self, organization):
        """Test evaluating non-existent transaction."""
        service = ComplianceService(organization)
        violations = service.evaluate_transaction(99999)

        assert violations == []


@pytest.mark.django_db
class TestResolveViolation:
    """Tests for violation resolution."""

    def test_resolve_violation(
        self, organization, supplier, category, admin_user, violation_factory
    ):
        """Test resolving a violation."""
        tx = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('10000.00'),
            invoice_number='TO-RESOLVE'
        )
        violation = violation_factory(tx)

        service = ComplianceService(organization)
        result = service.resolve_violation(
            violation.id,
            admin_user,
            'Approved by manager'
        )

        assert result is not None
        assert result['is_resolved'] is True
        assert result['resolution_notes'] == 'Approved by manager'

        # Verify in database
        violation.refresh_from_db()
        assert violation.is_resolved is True
        assert violation.resolved_by == admin_user

    def test_resolve_nonexistent_violation(self, organization, admin_user):
        """Test resolving non-existent violation."""
        service = ComplianceService(organization)
        result = service.resolve_violation(99999, admin_user, 'Notes')

        assert result is None


@pytest.mark.django_db
class TestSupplierComplianceScores:
    """Tests for supplier compliance scoring."""

    def test_supplier_scores(
        self, organization, supplier, category, admin_user, violation_factory
    ):
        """Test supplier compliance score calculation."""
        # Create transactions and violations
        for i in range(10):
            tx = TransactionFactory(
                organization=organization,
                supplier=supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'SCORE-{i}'
            )
            if i < 2:  # 20% violation rate
                violation_factory(tx)

        service = ComplianceService(organization)
        result = service.get_supplier_compliance_scores()

        assert len(result) >= 1
        supplier_score = [s for s in result if s['supplier_name'] == supplier.name]
        assert len(supplier_score) == 1
        assert 'compliance_score' in supplier_score[0]
        assert 'violation_count' in supplier_score[0]
        assert 'risk_level' in supplier_score[0]

    def test_supplier_scores_high_violations(
        self, organization, category, admin_user, violation_factory
    ):
        """Test supplier with many violations gets low score."""
        bad_supplier = SupplierFactory(organization=organization, name='Bad Supplier')

        # Create mostly violating transactions
        for i in range(10):
            tx = TransactionFactory(
                organization=organization,
                supplier=bad_supplier,
                category=category,
                uploaded_by=admin_user,
                amount=Decimal('1000.00'),
                invoice_number=f'BAD-{i}'
            )
            if i < 8:  # 80% violation rate
                violation_factory(tx)

        service = ComplianceService(organization)
        result = service.get_supplier_compliance_scores()

        bad_score = [s for s in result if s['supplier_name'] == 'Bad Supplier']
        assert len(bad_score) == 1
        assert bad_score[0]['compliance_score'] < 50
        assert bad_score[0]['risk_level'] == 'high'

    def test_supplier_scores_empty(self, organization):
        """Test scores with no data."""
        service = ComplianceService(organization)
        result = service.get_supplier_compliance_scores()

        assert result == []


@pytest.mark.django_db
class TestPoliciesList:
    """Tests for policies list retrieval."""

    def test_get_policies(self, organization, policy_factory):
        """Test getting list of policies."""
        policy_factory(
            name='Test Policy 1',
            rules={'max_transaction_amount': 10000}
        )
        policy_factory(
            name='Test Policy 2',
            rules={'require_contract': True}
        )

        service = ComplianceService(organization)
        result = service.get_policies_list()

        assert len(result) == 2
        for policy in result:
            assert 'id' in policy
            assert 'name' in policy
            assert 'rules_summary' in policy

    def test_policies_empty(self, organization):
        """Test policies list with no policies."""
        service = ComplianceService(organization)
        result = service.get_policies_list()

        assert result == []


@pytest.mark.django_db
class TestOrganizationScoping:
    """Tests for organization data isolation."""

    def test_violations_scoped_to_organization(
        self, organization, other_organization, supplier, category, admin_user,
        other_org_user, violation_factory
    ):
        """Test that violations are scoped to organization."""
        # Create violation in main org
        tx1 = TransactionFactory(
            organization=organization,
            supplier=supplier,
            category=category,
            uploaded_by=admin_user,
            amount=Decimal('10000.00'),
            invoice_number='ORG-VIOL'
        )
        violation_factory(tx1)

        # Create violation in other org
        other_supplier = SupplierFactory(organization=other_organization)
        other_category = CategoryFactory(organization=other_organization)
        other_policy = SpendingPolicy.objects.create(
            organization=other_organization,
            name='Other Policy',
            rules={}
        )
        tx2 = TransactionFactory(
            organization=other_organization,
            supplier=other_supplier,
            category=other_category,
            uploaded_by=other_org_user,
            amount=Decimal('10000.00'),
            invoice_number='OTHER-VIOL'
        )
        PolicyViolation.objects.create(
            organization=other_organization,
            transaction=tx2,
            policy=other_policy,
            violation_type='amount_exceeded',
            severity='high'
        )

        # Main org should only see its violation
        service = ComplianceService(organization)
        result = service.get_policy_violations()

        assert len(result) == 1
        assert result[0]['transaction_id'] == tx1.id

    def test_policies_scoped_to_organization(
        self, organization, other_organization, policy_factory
    ):
        """Test that policies are scoped to organization."""
        policy_factory(name='Main Org Policy')

        SpendingPolicy.objects.create(
            organization=other_organization,
            name='Other Org Policy',
            rules={}
        )

        service = ComplianceService(organization)
        result = service.get_policies_list()

        assert len(result) == 1
        assert result[0]['name'] == 'Main Org Policy'
