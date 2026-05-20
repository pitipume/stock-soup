from celery import Celery
from app.config import settings

celery_app = Celery(
    "stocksoup",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.scan_tasks", "app.tasks.bot_tasks", "app.tasks.lab_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "bot-cycle-every-5-minutes": {
            "task": "tasks.run_bot_cycle",
            "schedule": 300,  # seconds
        },
        "sync-positions-every-minute": {
            "task": "tasks.sync_positions",
            "schedule": 60,  # seconds
        },
    },
)
