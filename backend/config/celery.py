"""
Celery configuration for background tasks
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("analytics_dashboard")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "nightly-insight-generation": {
        "task": "batch_generate_insights",
        "schedule": crontab(hour=2, minute=0),
    },
    "nightly-insight-enhancement": {
        "task": "batch_enhance_insights",
        "schedule": crontab(hour=2, minute=30),
    },
    "cleanup-semantic-cache": {
        "task": "cleanup_semantic_cache",
        "schedule": crontab(hour=3, minute=0),
    },
    "cleanup-llm-logs": {
        "task": "cleanup_llm_request_logs",
        "schedule": crontab(hour=3, minute=30),
    },
    "weekly-rag-refresh": {
        "task": "refresh_rag_documents",
        "schedule": crontab(hour=4, minute=0, day_of_week="sunday"),
    },
    # Daily LLM cost digest at 06:00 UTC -- runs AFTER the 02:00 / 02:30 batch
    # jobs so it captures their cost in yesterday's window. Surfaces runaway
    # spend the morning after, not days later.
    "llm-cost-digest-daily": {
        "task": "send_llm_cost_digest",
        "schedule": crontab(hour=6, minute=0),
    },
    # Hourly tick to fire any is_scheduled=True Report whose next_run has
    # passed. Without this, scheduled reports created via the UI silently
    # never run. Companion task reschedule_report (chained on success in
    # generate_report_async) advances next_run by frequency.
    "process-scheduled-reports": {
        "task": "process_scheduled_reports",
        "schedule": crontab(minute=0),
    },
    # Nightly cleanup of completed non-scheduled reports older than 30 days.
    # Pairs with above so report storage doesn't grow unbounded.
    "cleanup-expired-reports": {
        "task": "cleanup_expired_reports",
        "schedule": crontab(hour=1, minute=0),
    },
}
