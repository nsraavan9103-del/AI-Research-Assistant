"""
Celery app configuration.
Workers are optional — if CELERY_ENABLED is False, indexing runs synchronously.
"""
from celery import Celery
from core.config import settings

celery_app = Celery(
    "rag_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.indexing", "tasks.email"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,            # Acknowledge only after completion
    worker_prefetch_multiplier=1,   # One heavy task per worker
    task_routes={
        "tasks.indexing.*": {"queue": "indexing"},
        "tasks.email.*":    {"queue": "email"},
    },
    task_retry_policy={
        "max_retries": 3,
        "interval_start": 5,
        "interval_step": 10,
    },
)
