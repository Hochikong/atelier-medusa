from celery import Celery
from loguru import logger
from celery.signals import worker_process_init, worker_process_shutdown
from MCF2Flash.mcf_2f.mcf_2f_core import MCF2FlashCore
from MCF2Flash.loguru_setup import loguru_setup
from MCF2Flash.app_config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, MCF2F_CONFIG

_mcf_core_instance: MCF2FlashCore = None


def get_mcf():
    global _mcf_core_instance
    if _mcf_core_instance is None:
        raise RuntimeError("Driver not initialized yet")
    return _mcf_core_instance


def init_mcf():
    global _mcf_core_instance
    _mcf_core_instance = MCF2FlashCore(logger, MCF2F_CONFIG)


def close_mcf():
    global _mcf_core_instance
    if _mcf_core_instance is not None:
        _mcf_core_instance.dispose()
        _mcf_core_instance = None


celery_app = Celery(
    "MCF-2-Flash",
    broker=str(CELERY_BROKER_URL),
    backend=str(CELERY_RESULT_BACKEND),
    include=["MCF2Flash.celery_misc.tasks", "MCF2Flash.celery_misc.mcf_v2_tasks"]
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
)


@worker_process_init.connect
def init_mcf_obj(**_):
    loguru_setup('celery_core')
    # 只在每个 Worker 子进程里执行一次
    init_mcf()


@worker_process_shutdown.connect
def shutdown_mcf_obj(**_):
    close_mcf()


celery_app.autodiscover_tasks()
