"""Finding D1: scheduled reports must advance next_run after each run.

Without this, process_scheduled_reports re-queues the same report on every
Celery Beat tick because next_run remains in the past forever.

Refs: docs/codebase-review-2026-05-04-highs-verified.md Finding D1
"""
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from apps.reports.models import Report
from apps.reports.tasks import generate_report_async, process_scheduled_reports


@pytest.fixture
def overdue_scheduled_report(db, organization, admin_user):
    """A scheduled report whose next_run is in the past (i.e., due now)."""
    return Report.objects.create(
        organization=organization,
        created_by=admin_user,
        name='Daily Spend Report',
        report_type='spend_analysis',
        status='scheduled',
        is_scheduled=True,
        schedule_frequency='daily',
        next_run=timezone.now() - timedelta(hours=1),
    )


@pytest.mark.django_db
class TestScheduledReportAdvancement:
    """Finding D1 regression suite."""

    @patch('apps.reports.services.ReportingService')
    def test_generate_report_async_advances_next_run(
        self, mock_service_class, overdue_scheduled_report
    ):
        """After generate runs successfully, next_run must move to the future."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_report_data.return_value = None

        original_next_run = overdue_scheduled_report.next_run

        result = generate_report_async(str(overdue_scheduled_report.pk))

        assert result['status'] == 'completed'

        overdue_scheduled_report.refresh_from_db()
        assert overdue_scheduled_report.next_run > timezone.now(), (
            f"next_run did not advance into the future. Was {original_next_run}, "
            f"is now {overdue_scheduled_report.next_run}."
        )
        assert overdue_scheduled_report.next_run != original_next_run, (
            "next_run is unchanged - rescheduling did not fire."
        )
        assert overdue_scheduled_report.last_run is not None, (
            "last_run should be set after a successful generation."
        )
        assert overdue_scheduled_report.status == 'scheduled', (
            "Scheduled reports should remain in 'scheduled' status after a run, "
            "not stay 'completed' (otherwise process_scheduled_reports won't pick "
            "them up next cadence)."
        )

    @patch('apps.reports.services.ReportingService')
    def test_process_scheduled_reports_does_not_double_queue_after_run(
        self, mock_service_class, overdue_scheduled_report
    ):
        """After a report runs once, the next process_scheduled_reports tick
        must NOT re-queue it (because next_run is now in the future)."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_report_data.return_value = None

        generate_report_async(str(overdue_scheduled_report.pk))

        with patch('apps.reports.tasks.generate_report_async') as mock_task:
            mock_task.delay = MagicMock()
            result = process_scheduled_reports()

        assert result['processed'] == 0, (
            "process_scheduled_reports re-queued a report whose next_run "
            "should have advanced into the future."
        )
        mock_task.delay.assert_not_called()

    def test_one_off_report_does_not_attempt_to_reschedule(
        self, organization, admin_user
    ):
        """Non-scheduled reports must NOT have next_run touched (they have none)."""
        with patch('apps.reports.services.ReportingService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.generate_report_data.return_value = None

            one_off = Report.objects.create(
                organization=organization,
                created_by=admin_user,
                name='One-off Report',
                report_type='spend_analysis',
                status='generating',
                is_scheduled=False,
            )

            result = generate_report_async(str(one_off.pk))

        assert result['status'] == 'completed'

        one_off.refresh_from_db()
        assert one_off.next_run is None, (
            "One-off reports should not have next_run set."
        )
        assert one_off.is_scheduled is False

    @patch('apps.reports.services.ReportingService')
    def test_failed_scheduled_report_still_advances_next_run(
        self, mock_service_class, overdue_scheduled_report
    ):
        """If generation permanently fails (retries exhausted), next_run must
        still advance so the system retries on the next cadence rather than
        infinite-looping on the failed run OR permanently disabling scheduling.
        """
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_report_data.side_effect = Exception('Permanent failure')

        original_next_run = overdue_scheduled_report.next_run

        # Skip the retry loop so we immediately hit the final-failure path.
        with patch.object(generate_report_async, 'max_retries', 0):
            result = generate_report_async(str(overdue_scheduled_report.pk))

        assert result['status'] == 'failed'

        overdue_scheduled_report.refresh_from_db()
        assert overdue_scheduled_report.next_run > timezone.now(), (
            "After a permanent failure, next_run should still advance to the "
            "next cadence so the system retries (not infinite-loop, not stuck)."
        )
        assert overdue_scheduled_report.next_run != original_next_run

    @patch('apps.reports.services.ReportingService')
    def test_failed_scheduled_report_picked_up_next_cadence(
        self, mock_service_class, overdue_scheduled_report
    ):
        """A scheduled report that failed once should be picked up at next cadence,
        not permanently disabled."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_report_data.side_effect = Exception('Transient')

        with patch.object(generate_report_async, 'max_retries', 0):
            generate_report_async(str(overdue_scheduled_report.pk))

        overdue_scheduled_report.refresh_from_db()
        # Force next_run back into the past to simulate cadence elapsing.
        overdue_scheduled_report.next_run = timezone.now() - timedelta(minutes=1)
        overdue_scheduled_report.save(update_fields=['next_run'])

        with patch('apps.reports.tasks.generate_report_async') as mock_task:
            mock_task.delay = MagicMock()
            result = process_scheduled_reports()

        assert result['processed'] == 1, (
            "Scheduled reports that failed once should still be retried at the "
            "next cadence, not permanently dropped from the schedule."
        )
