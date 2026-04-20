"""
Tests for Report model.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from apps.reports.models import Report


@pytest.mark.django_db
class TestReportModel:
    """Tests for Report model CRUD operations."""

    def test_create_report(self, organization, admin_user):
        """Test creating a basic report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            report_format='pdf',
            name='Test Spend Analysis',
            description='Test report description'
        )
        assert report.id is not None
        assert report.status == 'draft'
        assert report.organization == organization
        assert report.created_by == admin_user

    def test_report_auto_generate_name(self, organization, admin_user):
        """Test that report name is auto-generated if not provided."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='executive_summary'
        )
        # Name should contain report type display name
        assert 'Executive Summary' in report.name

    def test_report_type_choices(self, organization, admin_user):
        """Test all valid report type choices."""
        report_types = [
            'spend_analysis', 'supplier_performance', 'savings_opportunities',
            'price_trends', 'contract_compliance', 'executive_summary',
            'pareto_analysis', 'stratification', 'seasonality',
            'year_over_year', 'tail_spend', 'custom',
            'p2p_pr_status', 'p2p_po_compliance', 'p2p_ap_aging'
        ]
        for rt in report_types:
            report = Report.objects.create(
                organization=organization,
                created_by=admin_user,
                report_type=rt,
                name=f'Test {rt}'
            )
            assert report.report_type == rt

    def test_report_format_choices(self, organization, admin_user):
        """Test all valid report format choices."""
        for fmt in ['pdf', 'xlsx', 'csv']:
            report = Report.objects.create(
                organization=organization,
                created_by=admin_user,
                report_type='spend_analysis',
                report_format=fmt,
                name=f'Test {fmt}'
            )
            assert report.report_format == fmt

    def test_report_status_choices(self, organization, admin_user):
        """Test all valid status choices."""
        for status in ['draft', 'generating', 'completed', 'failed', 'scheduled']:
            report = Report.objects.create(
                organization=organization,
                created_by=admin_user,
                report_type='spend_analysis',
                status=status,
                name=f'Test {status}'
            )
            assert report.status == status


@pytest.mark.django_db
class TestReportIsExpired:
    """Tests for Report.is_expired property."""

    def test_is_expired_false_for_recent(self, organization, admin_user):
        """Test that recent reports are not expired."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            generated_at=timezone.now()
        )
        assert report.is_expired is False

    def test_is_expired_true_for_old(self, organization, admin_user):
        """Test that reports older than 30 days are expired."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            generated_at=timezone.now() - timedelta(days=31)
        )
        assert report.is_expired is True

    def test_is_expired_boundary(self, organization, admin_user):
        """Test boundary case at exactly 30 days."""
        # Use 30 days minus a small buffer to account for test execution time
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            generated_at=timezone.now() - timedelta(days=30, seconds=-1)
        )
        # Should not be expired at exactly 30 days
        assert report.is_expired is False

    def test_is_expired_false_when_not_generated(self, organization, admin_user):
        """Test that ungenerated reports are not expired."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            generated_at=None
        )
        assert report.is_expired is False


@pytest.mark.django_db
class TestReportCalculateNextRun:
    """Tests for Report.calculate_next_run method."""

    def test_calculate_next_run_daily(self, organization, admin_user):
        """Test next run calculation for daily schedule."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='daily'
        )
        before = timezone.now()
        next_run = report.calculate_next_run()
        after = timezone.now()

        assert next_run is not None
        # Should be approximately 1 day from now
        expected = before + timedelta(days=1)
        assert abs((next_run - expected).total_seconds()) < 10

    def test_calculate_next_run_weekly(self, organization, admin_user):
        """Test next run calculation for weekly schedule."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='weekly'
        )
        before = timezone.now()
        next_run = report.calculate_next_run()

        expected = before + timedelta(weeks=1)
        assert abs((next_run - expected).total_seconds()) < 10

    def test_calculate_next_run_monthly(self, organization, admin_user):
        """Test next run calculation for monthly schedule."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='monthly'
        )
        before = timezone.now()
        next_run = report.calculate_next_run()

        expected = before + timedelta(days=30)
        assert abs((next_run - expected).total_seconds()) < 10

    def test_calculate_next_run_quarterly(self, organization, admin_user):
        """Test next run calculation for quarterly schedule."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_scheduled=True,
            schedule_frequency='quarterly'
        )
        before = timezone.now()
        next_run = report.calculate_next_run()

        expected = before + timedelta(days=90)
        assert abs((next_run - expected).total_seconds()) < 10


@pytest.mark.django_db
class TestReportStatusMethods:
    """Tests for Report status transition methods."""

    def test_mark_completed(self, organization, admin_user):
        """Test marking report as completed."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='generating'
        )
        summary_data = {'total_spend': 100000, 'supplier_count': 10}
        report.mark_completed(summary_data)

        report.refresh_from_db()
        assert report.status == 'completed'
        assert report.generated_at is not None
        assert report.summary_data == summary_data

    def test_mark_completed_without_data(self, organization, admin_user):
        """Test marking report as completed without summary data."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='generating'
        )
        report.mark_completed()

        report.refresh_from_db()
        assert report.status == 'completed'
        assert report.generated_at is not None

    def test_mark_failed(self, organization, admin_user):
        """Test marking report as failed."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='generating'
        )
        error_msg = 'Database connection failed'
        report.mark_failed(error_msg)

        report.refresh_from_db()
        assert report.status == 'failed'
        assert report.error_message == error_msg


@pytest.mark.django_db
class TestReportCanAccess:
    """Tests for Report.can_access method."""

    def test_can_access_creator(self, organization, admin_user):
        """Test that creator can access their report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        assert report.can_access(admin_user) is True

    def test_can_access_superuser(self, organization, admin_user, other_org_user, db):
        """Test that superuser can access any report."""
        from django.contrib.auth.models import User
        superuser = User.objects.create_superuser(
            username='superadmin',
            email='super@example.com',
            password='SuperPass123!'
        )
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        assert report.can_access(superuser) is True

    def test_can_access_public_report(self, organization, admin_user, user):
        """Test that any org user can access public reports."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            is_public=True
        )
        assert report.can_access(user) is True

    def test_can_access_shared_with(self, organization, admin_user, user):
        """Test that users in shared_with can access report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        report.shared_with.add(user)
        assert report.can_access(user) is True

    def test_cannot_access_other_org(self, organization, other_organization, admin_user, other_org_user):
        """Test that users from other org cannot access report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        assert report.can_access(other_org_user) is False

    def test_can_access_same_org_member(self, organization, admin_user, user):
        """Test that org members can access org reports."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        # User is in same organization, should have access via org membership
        assert report.can_access(user) is True


@pytest.mark.django_db
class TestReportFiltersAndParameters:
    """Tests for Report filters and parameters JSON fields."""

    def test_filters_json_field(self, organization, admin_user):
        """Test storing filters as JSON."""
        filters = {
            'supplier_ids': [1, 2, 3],
            'category_ids': [4, 5],
            'min_amount': 1000,
            'max_amount': 50000
        }
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            filters=filters
        )
        report.refresh_from_db()
        assert report.filters == filters
        assert report.filters['supplier_ids'] == [1, 2, 3]

    def test_parameters_json_field(self, organization, admin_user):
        """Test storing parameters as JSON."""
        parameters = {
            'top_n': 20,
            'include_charts': True,
            'use_fiscal_year': True
        }
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='supplier_performance',
            parameters=parameters
        )
        report.refresh_from_db()
        assert report.parameters == parameters

    def test_summary_data_json_field(self, organization, admin_user):
        """Test storing summary data as JSON."""
        summary_data = {
            'total_spend': 1500000.50,
            'supplier_count': 45,
            'top_suppliers': [
                {'name': 'Supplier A', 'spend': 500000},
                {'name': 'Supplier B', 'spend': 300000}
            ]
        }
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            summary_data=summary_data
        )
        report.refresh_from_db()
        assert report.summary_data == summary_data
        assert len(report.summary_data['top_suppliers']) == 2


@pytest.mark.django_db
class TestReportStringRepresentation:
    """Tests for Report __str__ method."""

    def test_str_representation(self, organization, admin_user):
        """Test string representation of report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            name='Q4 2024 Analysis'
        )
        str_repr = str(report)
        assert 'Q4 2024 Analysis' in str_repr
        assert 'Spend Analysis' in str_repr


@pytest.mark.django_db
class TestReportDateRange:
    """Tests for Report date range fields."""

    def test_period_dates(self, organization, admin_user):
        """Test setting period start and end dates."""
        from datetime import date
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31)
        )
        report.refresh_from_db()
        assert report.period_start == date(2024, 1, 1)
        assert report.period_end == date(2024, 12, 31)

    def test_period_dates_nullable(self, organization, admin_user):
        """Test that period dates can be null."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis'
        )
        assert report.period_start is None
        assert report.period_end is None
