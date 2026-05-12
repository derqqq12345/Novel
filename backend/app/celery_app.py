"""
Celery 애플리케이션 설정
"""
from celery import Celery

from backend.app.config import settings

celery_app = Celery(
    "novel_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.app.tasks.novel_tasks", "backend.app.tasks.export_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
