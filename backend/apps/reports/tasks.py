"""
Celery tasks for async report generation and scheduled reports.
Adapted from REPORTING_MODULE_REPLICATION_GUIDE.md
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report_async(self, report_id: str):
    """
    Generate a single report asynchronously.

    Args:
        report_id: UUID of the Report to generate

    Retries up to 3 times with 60 second delay on failure.
    """
    from .models import Report
    from .services import ReportingService

    try:
        report = Report.objects.select_related('organization', 'created_by').get(pk=report_id)
    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found")
        return {'status': 'error', 'message': 'Report not found'}

    logger.info(f"Starting generation for report {report_id} ({report.report_type})")

    try:
        service = ReportingService(report.organization, report.created_by)
        service.generate_report_data(report)

        logger.info(f"Report {report_id} generated successfully")
        return {
            'status': 'completed',
            'report_id': str(report.id),
            'report_type': report.report_type,
        }

    except Exception as e:
        logger.exception(f"Error generating report {report_id}: {e}")

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        # Final failure
        report.mark_failed(str(e))
        return {
            'status': 'failed',
            'report_id': str(report.id),
            'error': str(e),
        }


@shared_task
def process_scheduled_reports():
    """
    Process all scheduled reports that are due for execution.

    This task should be run periodically (e.g., every hour) via Celery Beat.
    It finds all reports with:
    - is_scheduled=True
    - status='scheduled'
    - next_run <= now

    For each due report, it queues an async generation task.
    """
    from .models import Report

    now = timezone.now()

    # Find due reports
    due_reports = Report.objects.filter(
        is_scheduled=True,
        status='scheduled',
        next_run__lte=now
    ).select_related('organization')

    count = due_reports.count()
    if count == 0:
        logger.debug("No scheduled reports due")
        return {'processed': 0}

    logger.info(f"Processing {count} scheduled reports")

    processed = 0
    for report in due_reports:
        try:
            # Queue async generation
            generate_report_async.delay(str(report.pk))
            processed += 1
            logger.info(f"Queued scheduled report {report.pk}")
        except Exception as e:
            logger.exception(f"Error queueing report {report.pk}: {e}")

    return {
        'processed': processed,
        'total_due': count,
    }


@shared_task
def cleanup_expired_reports(days_old: int = 30):
    """
    Clean up old completed reports.

    Args:
        days_old: Delete reports older than this many days (default: 30)

    This helps manage storage by removing stale report files.
    """
    from datetime import timedelta
    from .models import Report

    cutoff = timezone.now() - timedelta(days=days_old)

    # Find expired reports (completed and not scheduled)
    expired = Report.objects.filter(
        status='completed',
        is_scheduled=False,
        generated_at__lt=cutoff
    )

    count = expired.count()
    if count == 0:
        logger.debug("No expired reports to clean up")
        return {'deleted': 0}

    logger.info(f"Cleaning up {count} expired reports (older than {days_old} days)")

    # Delete reports
    deleted, _ = expired.delete()

    return {
        'deleted': deleted,
        'cutoff_date': str(cutoff),
    }


@shared_task
def reschedule_report(report_id: str):
    """
    Reschedule a report after successful generation.

    Called after generate_report_async completes for scheduled reports.
    Updates next_run time based on schedule_frequency.
    """
    from .models import Report

    try:
        report = Report.objects.get(pk=report_id, is_scheduled=True)
    except Report.DoesNotExist:
        return {'status': 'skipped', 'reason': 'Report not found or not scheduled'}

    report.last_run = timezone.now()
    report.calculate_next_run()
    report.status = 'scheduled'
    report.save(update_fields=['last_run', 'next_run', 'status'])

    logger.info(f"Report {report_id} rescheduled for {report.next_run}")

    return {
        'status': 'rescheduled',
        'report_id': str(report_id),
        'next_run': str(report.next_run),
    }
