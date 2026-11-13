"""Celery application, queues, and Beat schedule."""

from celery import Celery
from celery.schedules import crontab

from src.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "prism",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_routes={
        "prism-sync.*": {"queue": "prism-sync"},
        "prism-alerts.*": {"queue": "prism-alerts"},
        "prism-forecast.*": {"queue": "prism-forecast"},
        "prism-commitments.*": {"queue": "prism-commitments"},
        "prism-recommendations.*": {"queue": "prism-recommendations"},
        "prism-reports.*": {"queue": "prism-reports"},
        "prism-virtual-tags.*": {"queue": "prism-virtual-tags"},
        "prism-dlq.*": {"queue": "prism-dlq"},
    },
)

celery_app.conf.beat_schedule = {
    "schedule-daily-sync": {
        "task": "prism-sync.schedule_daily",
        "schedule": crontab(hour=6, minute=0),
    },
    "schedule-daily-commitments": {
        "task": "prism-commitments.schedule_daily",
        "schedule": crontab(hour=7, minute=0),
    },
    "schedule-daily-forecast": {
        "task": "prism-forecast.schedule_daily",
        "schedule": crontab(hour=7, minute=30),
    },
    "schedule-daily-recommendations": {
        "task": "prism-recommendations.schedule_daily",
        "schedule": crontab(hour=8, minute=0),
    },
    "schedule-daily-reports": {
        "task": "prism-reports.schedule_daily",
        "schedule": crontab(hour=9, minute=0),
    },
    "forecast-accuracy-monthly": {
        "task": "prism-forecast.compute_accuracy",
        "schedule": crontab(hour=10, minute=0, day_of_month=1),
    },
    "purge-old-data": {
        "task": "prism-sync.purge_old_data",
        "schedule": crontab(hour=2, minute=0),
    },
}

celery_app.autodiscover_tasks(["src.workers"], force=True)

# Register tasks defined with shared_task / explicit modules
from src.workers import (  # noqa: F401
    alerts_worker,
    commitments_worker,
    dlq_worker,
    forecast_worker,
    recommendations_worker,
    reports_worker,
    sync_worker,
    virtual_tags_worker,
)
