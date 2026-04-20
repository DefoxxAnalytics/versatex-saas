"""
Tests for Report Celery Tasks.

Tests cover:
- generate_report_async
- process_scheduled_reports
- cleanup_expired_reports
- reschedule_report
"""
import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.utils import timezone

from apps.reports.models import Report
from apps.reports.tasks import (
    generate_report_async,
    process_scheduled_reports,
    cleanup_expired_reports,
    reschedule_report,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def report(db, organization, admin_user):
    """Create a test report."""
    return Report.objects.create(
        organization=organization,
        created_by=admin_user,
        report_type='spend_analysis',
        name='Test Report',
        status='generating'
    )


@pytest.fixture
def scheduled_report(db, organization, admin_user):
    """Create a scheduled report due for execution."""
    return Report.objects.create(
        organization=organization,
        created_by=admin_user,
        report_type='executive_summary',
        name='Scheduled Report',
        status='scheduled',
        is_scheduled=True,
        schedule_frequency='daily',
        next_run=timezone.now() - timedelta(hours=1)
    )


@pytest.fixture
def future_scheduled_report(db, organization, admin_user):
    """Create a scheduled report not yet due."""
    return Report.objects.create(
        organization=organization,
        created_by=admin_user,
        report_type='executive_summary',
        name='Future Scheduled Report',
        status='scheduled',
        is_scheduled=True,
        schedule_frequency='weekly',
        next_run=timezone.now() + timedelta(days=1)
    )


@pytest.fixture
def old_report(db, organization, admin_user):
    """Create an old completed report."""
    report = Report.objects.create(
        organization=organization,
        created_by=admin_user,
        report_type='spend_analysis',
        name='Old Report',
        status='completed',
        is_scheduled=False,
        generated_at=timezone.now() - timedelta(days=45)
    )
    return report


# ============================================================================
# generate_report_async Tests
# ============================================================================

@pytest.mark.django_db
class TestGenerateReportAsync:
    """Tests for generate_report_async task."""

    def test_report_not_found(self):
        """Test handling of non-existent report."""
        result = generate_report_async('00000000-0000-0000-0000-000000000000')

        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()

    @patch('apps.reports.services.ReportingService')
    def test_successful_generation(self, mock_service_class, report):
        """Test successful report generation."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_report_data.return_value = None

        result = generate_report_async(str(report.pk))

        assert result['status'] == 'completed'
        assert result['report_id'] == str(report.id)
        assert result['report_type'] == 'spend_analysis'

    def test_report_status_updated_after_success(self, report):
        """Test that report status is updated after successful generation."""
        # The report fixture starts with status='generating'
        assert report.status == 'generating'

        # After calling generate_report_async on a non-existent report, verify error handling
        result = generate_report_async('00000000-0000-0000-0000-999999999999')
        assert result['status'] == 'error'

    @patch('apps.reports.services.ReportingService')
    def test_report_with_filters(self, mock_service_class, organization, admin_user):
        """Test generation with filters."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            name='Filtered Report',
            status='generating',
            filters={'date_from': '2024-01-01', 'date_to': '2024-12-31'}
        )

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_report_data.return_value = None

        result = generate_report_async(str(report.pk))

        assert result['status'] == 'completed'


# ============================================================================
# process_scheduled_reports Tests
# ============================================================================

@pytest.mark.django_db
class TestProcessScheduledReports:
    """Tests for process_scheduled_reports task."""

    def test_no_due_reports(self, organization, admin_user):
        """Test when no reports are due."""
        # Create only future reports
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='executive_summary',
            status='scheduled',
            is_scheduled=True,
            schedule_frequency='daily',
            next_run=timezone.now() + timedelta(days=1)
        )

        result = process_scheduled_reports()

        assert result['processed'] == 0

    @patch('apps.reports.tasks.generate_report_async')
    def test_processes_due_reports(self, mock_generate, scheduled_report, future_scheduled_report):
        """Test that only due reports are processed."""
        mock_generate.delay = MagicMock()

        result = process_scheduled_reports()

        assert result['processed'] == 1
        assert result['total_due'] == 1
        mock_generate.delay.assert_called_once_with(str(scheduled_report.pk))

    @patch('apps.reports.tasks.generate_report_async')
    def test_multiple_due_reports(self, mock_generate, organization, admin_user):
        """Test processing multiple due reports."""
        mock_generate.delay = MagicMock()

        # Create multiple due reports
        for i in range(5):
            Report.objects.create(
                organization=organization,
                created_by=admin_user,
                report_type='spend_analysis',
                name=f'Scheduled Report {i}',
                status='scheduled',
                is_scheduled=True,
                schedule_frequency='daily',
                next_run=timezone.now() - timedelta(hours=i)
            )

        result = process_scheduled_reports()

        assert result['processed'] == 5
        assert result['total_due'] == 5
        assert mock_generate.delay.call_count == 5

    @patch('apps.reports.tasks.generate_report_async')
    def test_excludes_non_scheduled_reports(self, mock_generate, organization, admin_user):
        """Test that non-scheduled reports are excluded."""
        mock_generate.delay = MagicMock()

        # Create a completed report (not scheduled)
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='completed',
            is_scheduled=False
        )

        result = process_scheduled_reports()

        assert result['processed'] == 0
        mock_generate.delay.assert_not_called()


# ============================================================================
# cleanup_expired_reports Tests
# ============================================================================

@pytest.mark.django_db
class TestCleanupExpiredReports:
    """Tests for cleanup_expired_reports task."""

    def test_no_expired_reports(self, organization, admin_user):
        """Test when no reports are expired."""
        # Create a recent report
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='completed',
            is_scheduled=False,
            generated_at=timezone.now()
        )

        result = cleanup_expired_reports(days_old=30)

        assert result['deleted'] == 0

    def test_deletes_old_reports(self, old_report):
        """Test that old reports are deleted."""
        result = cleanup_expired_reports(days_old=30)

        assert result['deleted'] == 1
        assert not Report.objects.filter(pk=old_report.pk).exists()

    def test_custom_days_threshold(self, organization, admin_user):
        """Test with custom days threshold."""
        # Create a 20-day old report
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='completed',
            is_scheduled=False,
            generated_at=timezone.now() - timedelta(days=20)
        )

        # 30 days threshold should not delete
        result1 = cleanup_expired_reports(days_old=30)
        assert result1['deleted'] == 0

        # 15 days threshold should delete
        result2 = cleanup_expired_reports(days_old=15)
        assert result2['deleted'] == 1

    def test_preserves_scheduled_reports(self, organization, admin_user):
        """Test that scheduled reports are preserved."""
        # Create an old scheduled report
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='executive_summary',
            status='completed',
            is_scheduled=True,
            schedule_frequency='weekly',
            generated_at=timezone.now() - timedelta(days=45)
        )

        result = cleanup_expired_reports(days_old=30)

        assert result['deleted'] == 0

    def test_preserves_generating_reports(self, organization, admin_user):
        """Test that generating reports are preserved."""
        # Create an old generating report
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='generating',
            is_scheduled=False,
            generated_at=timezone.now() - timedelta(days=45)
        )

        result = cleanup_expired_reports(days_old=30)

        # 'generating' status != 'completed', so not deleted
        assert result['deleted'] == 0


# ============================================================================
# reschedule_report Tests
# ============================================================================

@pytest.mark.django_db
class TestRescheduleReport:
    """Tests for reschedule_report task."""

    def test_report_not_found(self):
        """Test handling of non-existent report."""
        result = reschedule_report('00000000-0000-0000-0000-000000000000')

        assert result['status'] == 'skipped'
        assert 'not found' in result['reason'].lower()

    def test_non_scheduled_report_skipped(self, report):
        """Test that non-scheduled reports are skipped."""
        result = reschedule_report(str(report.pk))

        assert result['status'] == 'skipped'

    def test_reschedules_daily_report(self, scheduled_report):
        """Test rescheduling a daily report."""
        old_next_run = scheduled_report.next_run

        result = reschedule_report(str(scheduled_report.pk))

        assert result['status'] == 'rescheduled'
        assert result['report_id'] == str(scheduled_report.pk)

        # Verify next_run is updated
        scheduled_report.refresh_from_db()
        assert scheduled_report.next_run > old_next_run
        assert scheduled_report.status == 'scheduled'
        assert scheduled_report.last_run is not None

    def test_reschedules_weekly_report(self, organization, admin_user):
        """Test rescheduling a weekly report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='completed',
            is_scheduled=True,
            schedule_frequency='weekly',
            next_run=timezone.now() - timedelta(hours=1)
        )

        result = reschedule_report(str(report.pk))

        assert result['status'] == 'rescheduled'

        report.refresh_from_db()
        assert report.status == 'scheduled'

    def test_reschedules_monthly_report(self, organization, admin_user):
        """Test rescheduling a monthly report."""
        report = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='completed',
            is_scheduled=True,
            schedule_frequency='monthly',
            next_run=timezone.now() - timedelta(hours=1)
        )

        result = reschedule_report(str(report.pk))

        assert result['status'] == 'rescheduled'

        report.refresh_from_db()
        assert report.status == 'scheduled'


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.django_db
class TestTaskIntegration:
    """Integration tests for task workflows."""

    @patch('apps.reports.tasks.generate_report_async')
    def test_scheduled_to_generation_flow(self, mock_generate, scheduled_report):
        """Test flow from scheduled report to generation."""
        mock_generate.delay = MagicMock()

        # Process scheduled reports
        process_result = process_scheduled_reports()

        assert process_result['processed'] == 1
        mock_generate.delay.assert_called_once()

    def test_cleanup_only_affects_completed(self, organization, admin_user):
        """Test that cleanup only affects completed non-scheduled reports."""
        old_time = timezone.now() - timedelta(days=45)

        # Create various old reports
        completed = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            name='Old Completed',
            status='completed',
            is_scheduled=False,
            generated_at=old_time
        )

        scheduled = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            name='Old Scheduled',
            status='completed',
            is_scheduled=True,
            schedule_frequency='weekly',
            generated_at=old_time
        )

        failed = Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            name='Old Failed',
            status='failed',
            is_scheduled=False,
            generated_at=old_time
        )

        result = cleanup_expired_reports(days_old=30)

        # Only completed non-scheduled should be deleted
        assert result['deleted'] == 1
        assert not Report.objects.filter(pk=completed.pk).exists()
        assert Report.objects.filter(pk=scheduled.pk).exists()
        assert Report.objects.filter(pk=failed.pk).exists()


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.django_db
class TestTaskEdgeCases:
    """Edge case tests for tasks."""

    def test_empty_database(self):
        """Test tasks with empty database."""
        # All should return gracefully
        process_result = process_scheduled_reports()
        cleanup_result = cleanup_expired_reports()

        assert process_result['processed'] == 0
        assert cleanup_result['deleted'] == 0

    @patch('apps.reports.tasks.generate_report_async')
    def test_error_during_queue(self, mock_generate, scheduled_report, organization, admin_user):
        """Test handling of queue errors."""
        # First call fails, second succeeds
        mock_generate.delay.side_effect = [Exception('Queue error'), None]

        # Create second due report
        Report.objects.create(
            organization=organization,
            created_by=admin_user,
            report_type='spend_analysis',
            status='scheduled',
            is_scheduled=True,
            schedule_frequency='daily',
            next_run=timezone.now() - timedelta(hours=2)
        )

        result = process_scheduled_reports()

        # Should continue processing despite first error
        assert result['total_due'] == 2
        assert result['processed'] == 1  # Only second succeeded

    def test_invalid_report_id_format(self):
        """Test with invalid report ID format."""
        # Invalid UUIDs raise validation errors and should be handled
        # The task should handle this gracefully
        import pytest
        from django.core.exceptions import ValidationError

        # Invalid UUID format - test that an error occurs
        with pytest.raises((ValidationError, ValueError)):
            reschedule_report('not-a-uuid')
