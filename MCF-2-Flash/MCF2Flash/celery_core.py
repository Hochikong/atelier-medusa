from celery import Celery

from MCF2Flash.app_config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "MCF-2-Flash",
    broker=str(CELERY_BROKER_URL),
    backend=str(CELERY_RESULT_BACKEND),
    include=["MCF2Flash.celery_misc.tasks"]
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
)