import traceback
from loguru import logger
from fastapi import APIRouter, HTTPException

from MCF2Flash.celery_misc.tasks import long_running_task, add, must_failed

router = APIRouter()


@router.post("/testing", tags=['BasicTest'])
def receive_task():
    try:
        task = long_running_task.delay(2)
        logger.info("Run a long task")
        return {"celery_task_id": task.id}
    except Exception:
        raise HTTPException(status_code=404, detail=traceback.format_exc())


@router.post("/add", tags=['BasicTest'])
def submit_add(x: int, y: int):
    task = add.delay(x, y)
    return {"celery_task_id": task.id}


@router.post("/must_failed", tags=['BasicTest'])
def submit_add(x: int, y: int):
    task = must_failed.delay(x, y)
    return {"celery_task_id": task.id}
