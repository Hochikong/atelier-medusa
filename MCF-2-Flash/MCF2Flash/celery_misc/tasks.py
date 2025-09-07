import pathlib
import sys
import time
import logging
t = pathlib.Path(__file__).parent.resolve()
sys.path.append("..")
sys.path.append(str(t))

from MCF2Flash.celery_core import celery_app

logger = logging.getLogger(__name__)

# region Framework Testing Methods
@celery_app.task(name="long_running_task")
def long_running_task(seconds: int):
    import time
    time.sleep(seconds)
    logger.info(f"WORKER: Slept for {seconds} seconds")
    return f"Slept for {seconds} seconds"


@celery_app.task(name="add")
def add(x: int, y: int) -> int:
    time.sleep(5)
    return x + y


@celery_app.task(name="must_failed")
def must_failed() -> int:
    time.sleep(5)
    raise RuntimeError("This is a test")

# endregion
