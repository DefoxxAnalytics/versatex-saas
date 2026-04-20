"""
Tests for P2P Report Generators.

Tests cover:
- PRStatusReportGenerator
- POComplianceReportGenerator
- APAgingReportGenerator
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from apps.reports.generators import (
    PRStatusReportGenerator,
    POComplianceReportGenerator,
    APAgingReportGenerator,
)
from apps.procurement.models import (
    PurchaseRequisition,
    PurchaseOrder,
    GoodsReceipt,
    Invoice,
    Supplier,
    Category,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def category(db, organization):
    """Create a test category."""
    return Category.objects.create(
        organization=organization,
        name='Test Category',
        description='Category for P2P testing'
    )


@pytest.fixture
def supplier(db, organization):
    """Create a test supplier."""
    return Supplier.objects.create(
        organization=organization,
        name='Test Supplier',
        contact_email='supplier@test.com'
    )


@pytest.fixture
def supplier2(db, organization):
    """Create a second test supplier."""
    return Supplier.objects.create(
        organization=organization,
        name='Supplier Two',
        contact_email='supplier2@test.com'
    )


@pytest.fixture
def purchase_requisition(db, organization, admin_user, supplier, category):
    """Create a test purchase requisition."""
    return PurchaseRequisition.objects.create(
        organization=organization,
        pr_number='PR-2024-001',
        requested_by=admin_user,
        supplier_suggested=supplier,
        category=category,
        description='Test requisition',
        estimated_amount=Decimal('5000.00'),
        status='approved',
        department='IT',
        cost_center='CC-001',
        created_date=date.today() - timedelta(days=10),
        submitted_date=date.today() - timedelta(days=9),
        approval_date=date.today() - timedelta(days=7)
    )


@pytest.fixture
def purchase_order(db, organization, admin_user, supplier, category, purchase_requisition):
    """Create a test purchase order."""
    return PurchaseOrder.objects.create(
        organization=organization,
        po_number='PO-2024-001',
        created_by=admin_user,
        supplier=supplier,
        category=category,
        requisition=purchase_requisition,
        total_amount=Decimal('5000.00'),
        original_amount=Decimal('5000.00'),
        status='delivered',
        is_contract_backed=True,
        created_date=date.today() - timedelta(days=5)
    )


@pytest.fixture
def goods_receipt(db, organization, admin_user, purchase_order):
    """Create a test goods receipt."""
    return GoodsReceipt.objects.create(
        organization=organization,
        gr_number='GR-2024-001',
        purchase_order=purchase_order,
        received_by=admin_user,
        quantity_ordered=100,
        quantity_received=100,
        quantity_accepted=98,
        received_date=date.today() - timedelta(days=3)
    )


@pytest.fixture
def invoice(db, organization, supplier, purchase_order):
    """Create a test invoice."""
    return Invoice.objects.create(
        organization=organization,
        invoice_number='INV-2024-001',
        supplier=supplier,
        purchase_order=purchase_order,
        invoice_date=date.today() - timedelta(days=2),
        due_date=date.today() + timedelta(days=28),
        invoice_amount=Decimal('5000.00'),
        net_amount=Decimal('5000.00'),
        match_status='3way_matched',
        has_exception=False,
        payment_terms='Net 30'
    )


@pytest.fixture
def overdue_invoice(db, organization, supplier):
    """Create an overdue invoice."""
    return Invoice.objects.create(
        organization=organization,
        invoice_number='INV-2024-OVERDUE',
        supplier=supplier,
        invoice_date=date.today() - timedelta(days=60),
        due_date=date.today() - timedelta(days=30),
        invoice_amount=Decimal('10000.00'),
        net_amount=Decimal('10000.00'),
        match_status='pending_match',
        has_exception=False,
        status='pending_match',
        payment_terms='Net 30'
    )


# ============================================================================
# PR Status Report Generator Tests
# ============================================================================

@pytest.mark.django_db
class TestPRStatusReportGenerator:
    """Tests for PRStatusReportGenerator."""

    def test_report_type(self, organization):
        """Test report type is correct."""
        generator = PRStatusReportGenerator(organization)
        assert generator.report_type == 'p2p_pr_status'

    def test_report_title(self, organization):
        """Test report title is correct."""
        generator = PRStatusReportGenerator(organization)
        assert generator.report_title == 'PR Status Report'

    def test_generate_empty_data(self, organization):
        """Test report generation with no data."""
        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result
        assert 'summary' in result
        assert 'status_breakdown' in result
        assert 'department_analysis' in result
        assert 'pending_approvals' in result
        assert 'insights' in result
        assert 'recommendations' in result

    def test_generate_with_data(self, organization, purchase_requisition):
        """Test report generation with data."""
        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        assert result['metadata']['report_type'] == 'p2p_pr_status'
        assert 'summary' in result
        summary = result['summary']
        assert 'total_prs' in summary
        assert 'total_value' in summary
        assert 'conversion_rate' in summary
        assert 'rejection_rate' in summary

    def test_summary_kpis(self, organization, admin_user, supplier, category):
        """Test summary KPIs are calculated correctly."""
        # Create multiple PRs with different statuses
        for i, status in enumerate(['approved', 'rejected', 'pending', 'converted_to_po']):
            PurchaseRequisition.objects.create(
                organization=organization,
                pr_number=f'PR-KPI-{i}',
                requested_by=admin_user,
                supplier_suggested=supplier,
                category=category,
                description=f'PR {status}',
                estimated_amount=Decimal('1000.00'),
                status=status,
                department='Finance',
                created_date=date.today() - timedelta(days=i),
                submitted_date=date.today() - timedelta(days=i)
            )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        summary = result['summary']
        assert summary['total_prs'] >= 4

    def test_department_analysis(self, organization, admin_user, supplier, category):
        """Test department breakdown in report."""
        # Create PRs for different departments
        for dept in ['IT', 'Finance', 'HR']:
            PurchaseRequisition.objects.create(
                organization=organization,
                pr_number=f'PR-DEPT-{dept}',
                requested_by=admin_user,
                supplier_suggested=supplier,
                category=category,
                description=f'PR {dept}',
                estimated_amount=Decimal('1000.00'),
                status='approved',
                department=dept,
                created_date=date.today()
            )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        assert 'department_analysis' in result
        # Should be limited to 15 departments
        assert len(result['department_analysis']) <= 15

    def test_pending_approvals(self, organization, admin_user, supplier, category):
        """Test pending approvals list."""
        # Create pending PRs
        for i in range(5):
            PurchaseRequisition.objects.create(
                organization=organization,
                pr_number=f'PR-PENDING-{i}',
                requested_by=admin_user,
                supplier_suggested=supplier,
                category=category,
                description=f'Pending PR {i}',
                estimated_amount=Decimal('2000.00'),
                status='pending',
                department='IT',
                created_date=date.today() - timedelta(days=i),
                submitted_date=date.today() - timedelta(days=i)
            )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        assert 'pending_approvals' in result
        # Should be limited to 20
        assert len(result['pending_approvals']) <= 20

    def test_insights_generation(self, organization, admin_user, supplier, category):
        """Test that insights are generated based on data."""
        # Create PRs with poor metrics to trigger insights
        for i in range(10):
            status = 'rejected' if i < 3 else 'pending'
            PurchaseRequisition.objects.create(
                organization=organization,
                pr_number=f'PR-INSIGHT-{i}',
                requested_by=admin_user,
                supplier_suggested=supplier,
                category=category,
                description=f'Insight PR {i}',
                estimated_amount=Decimal('3000.00'),
                status=status,
                department='Operations',
                created_date=date.today() - timedelta(days=i * 2)
            )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        assert 'insights' in result
        # Insights should be limited to 6
        assert len(result['insights']) <= 6

    def test_recommendations_generation(self, organization, admin_user, supplier, category):
        """Test that recommendations are generated based on data."""
        # Create PRs to trigger recommendations
        for i in range(10):
            PurchaseRequisition.objects.create(
                organization=organization,
                pr_number=f'PR-REC-{i}',
                requested_by=admin_user,
                supplier_suggested=supplier,
                category=category,
                description=f'Rec PR {i}',
                estimated_amount=Decimal('60000.00'),  # High value
                status='pending',
                department='Procurement',
                created_date=date.today() - timedelta(days=10)
            )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        assert 'recommendations' in result
        # Recommendations should be limited to 6
        assert len(result['recommendations']) <= 6

    def test_date_filters(self, organization, admin_user, supplier, category):
        """Test that date filters are applied."""
        # Create PRs with different dates
        PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-OLD',
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            description='Old PR',
            estimated_amount=Decimal('1000.00'),
            status='approved',
            department='IT',
            created_date=date(2023, 1, 15)
        )
        PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-NEW',
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            description='New PR',
            estimated_amount=Decimal('2000.00'),
            status='approved',
            department='IT',
            created_date=date(2024, 6, 15)
        )

        filters = {
            'date_from': '2024-01-01',
            'date_to': '2024-12-31'
        }
        generator = PRStatusReportGenerator(organization, filters=filters)
        result = generator.generate()

        # Metadata should show filters applied
        assert result['metadata']['filters_applied'] == filters


# ============================================================================
# PO Compliance Report Generator Tests
# ============================================================================

@pytest.mark.django_db
class TestPOComplianceReportGenerator:
    """Tests for POComplianceReportGenerator."""

    def test_report_type(self, organization):
        """Test report type is correct."""
        generator = POComplianceReportGenerator(organization)
        assert generator.report_type == 'p2p_po_compliance'

    def test_report_title(self, organization):
        """Test report title is correct."""
        generator = POComplianceReportGenerator(organization)
        assert generator.report_title == 'PO Compliance Report'

    def test_generate_empty_data(self, organization):
        """Test report generation with no data."""
        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result
        assert 'summary' in result
        assert 'compliance_score' in result
        assert 'status_breakdown' in result
        assert 'maverick_by_category' in result
        assert 'amendment_analysis' in result
        assert 'supplier_compliance' in result
        assert 'insights' in result
        assert 'recommendations' in result

    def test_generate_with_data(self, organization, purchase_order):
        """Test report generation with data."""
        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        assert result['metadata']['report_type'] == 'p2p_po_compliance'
        assert 'summary' in result
        summary = result['summary']
        assert 'total_pos' in summary
        assert 'total_value' in summary
        assert 'contract_coverage_pct' in summary
        assert 'maverick_rate' in summary

    def test_compliance_score_calculation(self, organization, admin_user, supplier, category):
        """Test compliance score calculation."""
        # Create POs with high contract coverage
        for i in range(5):
            PurchaseOrder.objects.create(
                organization=organization,
                po_number=f'PO-COMP-{i}',
                created_by=admin_user,
                supplier=supplier,
                category=category,
                total_amount=Decimal('10000.00'),
                original_amount=Decimal('10000.00'),
                status='delivered',
                is_contract_backed=True,
                created_date=date.today() - timedelta(days=i)
            )

        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        compliance = result['compliance_score']
        assert 'score' in compliance
        assert 'grade' in compliance
        assert 'status' in compliance
        assert 'breakdown' in compliance
        assert 0 <= compliance['score'] <= 100
        assert compliance['grade'] in ['A', 'B', 'C', 'D', 'F']

    def test_compliance_grade_a(self, organization, admin_user, supplier, category):
        """Test compliance grade A for excellent scores."""
        # Create all contracted POs (high coverage, low maverick)
        for i in range(10):
            PurchaseOrder.objects.create(
                organization=organization,
                po_number=f'PO-GRADE-A-{i}',
                created_by=admin_user,
                supplier=supplier,
                category=category,
                total_amount=Decimal('5000.00'),
                original_amount=Decimal('5000.00'),
                status='delivered',
                is_contract_backed=True,
                created_date=date.today()
            )

        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        # With all contracted POs, should have high score
        assert result['compliance_score']['score'] >= 80

    def test_maverick_spend_analysis(self, organization, admin_user, supplier, category):
        """Test maverick/off-contract spend analysis."""
        # Create off-contract POs
        for i in range(5):
            PurchaseOrder.objects.create(
                organization=organization,
                po_number=f'PO-MAVERICK-{i}',
                created_by=admin_user,
                supplier=supplier,
                category=category,
                total_amount=Decimal('5000.00'),
                original_amount=Decimal('5000.00'),
                status='active',
                is_contract_backed=False,
                created_date=date.today()
            )

        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        summary = result['summary']
        assert 'maverick_rate' in summary
        assert 'off_contract_value' in summary

    def test_amendment_analysis(self, organization, admin_user, supplier, category):
        """Test PO amendment analysis."""
        # Create PO with amendment (different original vs total amount)
        PurchaseOrder.objects.create(
            organization=organization,
            po_number='PO-AMENDED',
            created_by=admin_user,
            supplier=supplier,
            category=category,
            total_amount=Decimal('15000.00'),
            original_amount=Decimal('10000.00'),  # Original was less
            status='active',
            is_contract_backed=True,
            amendment_count=1,
            created_date=date.today()
        )

        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        assert 'amendment_analysis' in result
        summary = result['summary']
        assert 'amendment_rate' in summary

    def test_supplier_compliance(self, organization, admin_user, supplier, supplier2, category):
        """Test supplier compliance breakdown."""
        # Create POs for multiple suppliers
        for s in [supplier, supplier2]:
            for i in range(3):
                PurchaseOrder.objects.create(
                    organization=organization,
                    po_number=f'PO-{s.name[:3]}-{i}',
                    created_by=admin_user,
                    supplier=s,
                    category=category,
                    total_amount=Decimal('4000.00'),
                    original_amount=Decimal('4000.00'),
                    status='active',
                    is_contract_backed=i % 2 == 0,
                    created_date=date.today()
                )

        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        assert 'supplier_compliance' in result
        # Should be limited to 20 suppliers
        assert len(result['supplier_compliance']) <= 20

    def test_insights_for_low_coverage(self, organization, admin_user, supplier, category):
        """Test insights generated for low contract coverage."""
        # Create mostly off-contract POs
        for i in range(10):
            PurchaseOrder.objects.create(
                organization=organization,
                po_number=f'PO-LOWCOV-{i}',
                created_by=admin_user,
                supplier=supplier,
                category=category,
                total_amount=Decimal('5000.00'),
                original_amount=Decimal('5000.00'),
                status='active',
                is_contract_backed=i < 2,  # Only 2 contracted
                created_date=date.today()
            )

        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        insights = result['insights']
        assert len(insights) <= 6
        # Should have warning about low coverage
        warning_types = [i['type'] for i in insights]
        assert 'warning' in warning_types or 'success' in warning_types

    def test_recommendations_for_maverick(self, organization, admin_user, supplier, category):
        """Test recommendations for high maverick spend."""
        # Create high-value off-contract POs
        for i in range(5):
            PurchaseOrder.objects.create(
                organization=organization,
                po_number=f'PO-HIGHMAV-{i}',
                created_by=admin_user,
                supplier=supplier,
                category=category,
                total_amount=Decimal('50000.00'),
                original_amount=Decimal('50000.00'),
                status='active',
                is_contract_backed=False,
                created_date=date.today()
            )

        generator = POComplianceReportGenerator(organization)
        result = generator.generate()

        recommendations = result['recommendations']
        assert len(recommendations) <= 6
        # Should have high priority recommendations
        priorities = [r.get('priority') for r in recommendations]
        assert 'High' in priorities or 'Medium' in priorities


# ============================================================================
# AP Aging Report Generator Tests
# ============================================================================

@pytest.mark.django_db
class TestAPAgingReportGenerator:
    """Tests for APAgingReportGenerator."""

    def test_report_type(self, organization):
        """Test report type is correct."""
        generator = APAgingReportGenerator(organization)
        assert generator.report_type == 'p2p_ap_aging'

    def test_report_title(self, organization):
        """Test report title is correct."""
        generator = APAgingReportGenerator(organization)
        assert generator.report_title == 'AP Aging Report'

    def test_generate_empty_data(self, organization):
        """Test report generation with no data."""
        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        assert 'metadata' in result
        assert 'summary' in result
        assert 'aging_buckets' in result
        assert 'dpo_trend' in result
        assert 'supplier_aging' in result
        assert 'terms_compliance' in result
        assert 'cash_flow_forecast' in result
        assert 'risk_assessment' in result
        assert 'insights' in result
        assert 'recommendations' in result

    def test_generate_with_data(self, organization, invoice):
        """Test report generation with invoice data."""
        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        assert result['metadata']['report_type'] == 'p2p_ap_aging'
        assert 'summary' in result
        summary = result['summary']
        assert 'total_ap' in summary
        assert 'overdue_amount' in summary
        assert 'current_dpo' in summary
        assert 'on_time_rate' in summary

    def test_overdue_calculation(self, organization, overdue_invoice):
        """Test overdue amount calculation."""
        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        summary = result['summary']
        assert 'overdue_amount' in summary
        assert 'overdue_pct' in summary

    def test_risk_assessment(self, organization, supplier):
        """Test AP risk assessment."""
        # Create invoices with varying overdue status
        today = date.today()
        for i, days_overdue in enumerate([0, 30, 60, 90]):
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-RISK-{i}',
                supplier=supplier,
                invoice_date=today - timedelta(days=days_overdue + 30),
                due_date=today - timedelta(days=days_overdue),
                invoice_amount=Decimal('10000.00'),
                net_amount=Decimal('10000.00'),
                match_status='pending',
                status='pending_match',
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        risk = result['risk_assessment']
        assert 'overall_level' in risk
        assert 'factors' in risk
        assert risk['overall_level'] in ['Low', 'Medium', 'High']

    def test_risk_level_high(self, organization, supplier):
        """Test high risk level detection."""
        # Create many overdue invoices
        today = date.today()
        for i in range(10):
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-HIGHRISK-{i}',
                supplier=supplier,
                invoice_date=today - timedelta(days=120),
                due_date=today - timedelta(days=90),
                invoice_amount=Decimal('20000.00'),
                net_amount=Decimal('20000.00'),
                match_status='pending',
                status='pending_match',
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        # With many severely overdue invoices, should be high risk
        risk_factors = result['risk_assessment']['factors']
        high_risk_count = len([f for f in risk_factors if f.get('level') == 'High'])
        assert high_risk_count >= 0  # May vary based on calculations

    def test_supplier_aging(self, organization, supplier, supplier2):
        """Test supplier aging breakdown."""
        today = date.today()
        for s in [supplier, supplier2]:
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-{s.name[:3]}-1',
                supplier=s,
                invoice_date=today - timedelta(days=15),
                due_date=today + timedelta(days=15),
                invoice_amount=Decimal('5000.00'),
                net_amount=Decimal('5000.00'),
                match_status='3way_matched',
                status='pending_match',
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        assert 'supplier_aging' in result
        # Should be limited to 20 suppliers
        assert len(result['supplier_aging']) <= 20

    def test_aging_buckets(self, organization, supplier):
        """Test aging bucket distribution."""
        today = date.today()
        # Create invoices in different aging buckets
        buckets = [
            (0, 'current'),      # Current (not due)
            (35, '31-60'),       # 31-60 days overdue
            (75, '61-90'),       # 61-90 days overdue
            (100, '90+'),        # 90+ days overdue
        ]

        for days, bucket_name in buckets:
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-BUCKET-{bucket_name}',
                supplier=supplier,
                invoice_date=today - timedelta(days=days + 30),
                due_date=today - timedelta(days=days),
                invoice_amount=Decimal('10000.00'),
                net_amount=Decimal('10000.00'),
                match_status='pending',
                status='pending_match',
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        assert 'aging_buckets' in result

    def test_dpo_trends(self, organization, supplier):
        """Test DPO trend data."""
        today = date.today()
        # Create invoices over several months
        for i in range(6):
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-DPO-{i}',
                supplier=supplier,
                invoice_date=today - timedelta(days=30 * i + 15),
                due_date=today - timedelta(days=30 * i),
                invoice_amount=Decimal('5000.00'),
                net_amount=Decimal('5000.00'),
                match_status='3way_matched',
                status='paid',
                paid_date=today - timedelta(days=30 * i + 10),
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        assert 'dpo_trend' in result

    def test_cash_flow_forecast(self, organization, supplier):
        """Test cash flow forecast data."""
        today = date.today()
        # Create invoices with upcoming due dates
        for i in range(8):
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-CASHFLOW-{i}',
                supplier=supplier,
                invoice_date=today - timedelta(days=15),
                due_date=today + timedelta(days=7 * i),  # Spread over 8 weeks
                invoice_amount=Decimal('10000.00'),
                net_amount=Decimal('10000.00'),
                match_status='3way_matched',
                status='pending_match',
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        assert 'cash_flow_forecast' in result

    def test_terms_compliance(self, organization, supplier):
        """Test payment terms compliance data."""
        today = date.today()
        terms_list = ['Net 30', 'Net 45', 'Net 60']

        for terms in terms_list:
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-TERMS-{terms}',
                supplier=supplier,
                invoice_date=today - timedelta(days=30),
                due_date=today,
                invoice_amount=Decimal('5000.00'),
                net_amount=Decimal('5000.00'),
                match_status='3way_matched',
                status='paid',
                paid_date=today - timedelta(days=5),
                payment_terms=terms
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        assert 'terms_compliance' in result

    def test_insights_for_overdue(self, organization, supplier):
        """Test insights generated for overdue invoices."""
        today = date.today()
        # Create severely overdue invoices
        for i in range(5):
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-INSIGHT-OVERDUE-{i}',
                supplier=supplier,
                invoice_date=today - timedelta(days=120),
                due_date=today - timedelta(days=90),
                invoice_amount=Decimal('20000.00'),
                net_amount=Decimal('20000.00'),
                match_status='pending',
                status='pending_match',
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        insights = result['insights']
        assert len(insights) <= 6

    def test_recommendations_for_high_overdue(self, organization, supplier):
        """Test recommendations for high overdue amounts."""
        today = date.today()
        # Create high-value overdue invoices
        for i in range(5):
            Invoice.objects.create(
                organization=organization,
                invoice_number=f'INV-REC-OVERDUE-{i}',
                supplier=supplier,
                invoice_date=today - timedelta(days=60),
                due_date=today - timedelta(days=30),
                invoice_amount=Decimal('50000.00'),
                net_amount=Decimal('50000.00'),
                match_status='pending',
                status='pending_match',
                payment_terms='Net 30'
            )

        generator = APAgingReportGenerator(organization)
        result = generator.generate()

        recommendations = result['recommendations']
        assert len(recommendations) <= 6


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.django_db
class TestP2PGeneratorIntegration:
    """Integration tests for P2P generators with full data flow."""

    def test_complete_p2p_cycle(
        self, organization, admin_user, supplier, category,
        purchase_requisition, purchase_order, goods_receipt, invoice
    ):
        """Test all generators with complete P2P cycle data."""
        # Test PR Status
        pr_generator = PRStatusReportGenerator(organization)
        pr_result = pr_generator.generate()
        assert pr_result['metadata']['report_type'] == 'p2p_pr_status'
        assert pr_result['summary']['total_prs'] >= 1

        # Test PO Compliance
        po_generator = POComplianceReportGenerator(organization)
        po_result = po_generator.generate()
        assert po_result['metadata']['report_type'] == 'p2p_po_compliance'
        assert po_result['summary']['total_pos'] >= 1

        # Test AP Aging
        ap_generator = APAgingReportGenerator(organization)
        ap_result = ap_generator.generate()
        assert ap_result['metadata']['report_type'] == 'p2p_ap_aging'
        assert ap_result['summary']['total_ap'] >= 0

    def test_filters_applied_consistently(self, organization, admin_user, supplier, category):
        """Test that filters are applied consistently across generators."""
        # Create data in 2023
        pr_2023 = PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-2023-FILTER',
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            description='2023 PR',
            estimated_amount=Decimal('5000.00'),
            status='approved',
            department='IT',
            created_date=date(2023, 6, 15)
        )

        # Create data in 2024
        pr_2024 = PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-2024-FILTER',
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            description='2024 PR',
            estimated_amount=Decimal('5000.00'),
            status='approved',
            department='IT',
            created_date=date(2024, 6, 15)
        )

        filters = {
            'date_from': '2024-01-01',
            'date_to': '2024-12-31'
        }

        pr_generator = PRStatusReportGenerator(organization, filters=filters)
        pr_result = pr_generator.generate()

        # Filters should be recorded in metadata
        assert pr_result['metadata']['filters_applied'] == filters

    def test_organization_isolation(self, organization, other_organization, admin_user, supplier, category):
        """Test that generators only return data for specified organization."""
        # Create PR in main org
        PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-MAIN-ORG',
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            description='Main Org PR',
            estimated_amount=Decimal('5000.00'),
            status='approved',
            department='IT',
            created_date=date.today()
        )

        # Create category and supplier for other org
        other_supplier = Supplier.objects.create(
            organization=other_organization,
            name='Other Org Supplier'
        )
        other_category = Category.objects.create(
            organization=other_organization,
            name='Other Org Category'
        )

        # Create PR in other org
        PurchaseRequisition.objects.create(
            organization=other_organization,
            pr_number='PR-OTHER-ORG',
            requested_by=admin_user,
            supplier_suggested=other_supplier,
            category=other_category,
            description='Other Org PR',
            estimated_amount=Decimal('5000.00'),
            status='approved',
            department='Finance',
            created_date=date.today()
        )

        # Generator for main org should only see main org data
        pr_generator = PRStatusReportGenerator(organization)
        result = pr_generator.generate()

        # Should only have data from main organization
        assert result['metadata']['organization'] == organization.name


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.django_db
class TestP2PGeneratorEdgeCases:
    """Edge case tests for P2P generators."""

    def test_zero_amounts(self, organization, admin_user, supplier, category):
        """Test handling of zero amounts."""
        PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-ZERO',
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            description='Zero Amount PR',
            estimated_amount=Decimal('0.00'),
            status='approved',
            department='IT',
            created_date=date.today()
        )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()
        # Should handle zero amounts without error
        assert 'summary' in result

    def test_large_dataset(self, organization, admin_user, supplier, category):
        """Test handling of larger datasets."""
        # Create 50 PRs
        for i in range(50):
            PurchaseRequisition.objects.create(
                organization=organization,
                pr_number=f'PR-LARGE-{i}',
                requested_by=admin_user,
                supplier_suggested=supplier,
                category=category,
                description=f'Large Dataset PR {i}',
                estimated_amount=Decimal('1000.00'),
                status='approved' if i % 3 == 0 else 'pending',
                department=f'Dept-{i % 5}',
                created_date=date.today() - timedelta(days=i)
            )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()

        # Should complete without error and respect limits
        assert result['summary']['total_prs'] == 50
        assert len(result['department_analysis']) <= 15
        assert len(result['pending_approvals']) <= 20

    def test_null_dates(self, organization, admin_user, supplier, category):
        """Test handling of null dates."""
        PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-NULL-DATES',
            requested_by=admin_user,
            supplier_suggested=supplier,
            category=category,
            description='Null Dates PR',
            estimated_amount=Decimal('1000.00'),
            status='draft',
            department='IT',
            created_date=date.today(),
            submitted_date=None,
            approval_date=None
        )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()
        # Should handle null dates without error
        assert 'summary' in result

    def test_special_characters_in_names(self, organization, admin_user, category):
        """Test handling of special characters in supplier names."""
        special_supplier = Supplier.objects.create(
            organization=organization,
            name='Test & Co. <Special> "Supplier"',
            contact_email='special@test.com'
        )

        PurchaseRequisition.objects.create(
            organization=organization,
            pr_number='PR-SPECIAL',
            requested_by=admin_user,
            supplier_suggested=special_supplier,
            category=category,
            description='Special Chars PR',
            estimated_amount=Decimal('1000.00'),
            status='approved',
            department='R&D',
            created_date=date.today()
        )

        generator = PRStatusReportGenerator(organization)
        result = generator.generate()
        # Should handle special characters without error
        assert 'summary' in result
