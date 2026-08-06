from celery import Celery

from spine.config.settings import settings

celery_app = Celery(
    "spine",
    broker=settings.effective_celery_broker_url,
    include=["spine.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_always_eager,
)
