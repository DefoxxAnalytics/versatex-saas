"""
Celery configuration for background tasks
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('analytics_dashboard')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'nightly-insight-generation': {
        'task': 'batch_generate_insights',
        'schedule': crontab(hour=2, minute=0),
    },
    'nightly-insight-enhancement': {
        'task': 'batch_enhance_insights',
        'schedule': crontab(hour=2, minute=30),
    },
    'cleanup-semantic-cache': {
        'task': 'cleanup_semantic_cache',
        'schedule': crontab(hour=3, minute=0),
    },
    'cleanup-llm-logs': {
        'task': 'cleanup_llm_request_logs',
        'schedule': crontab(hour=3, minute=30),
    },
    'weekly-rag-refresh': {
        'task': 'refresh_rag_documents',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
    },
}
