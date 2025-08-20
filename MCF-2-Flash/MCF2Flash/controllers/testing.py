import traceback

from fastapi import APIRouter, HTTPException

from MCF2Flash.celery_misc.tasks import long_running_task

router = APIRouter()


@router.post("/testing", tags=['test'])
def receive_task():
    try:
        task = long_running_task.delay(2)
        return {"celery_task_id": task.id}
    except Exception:
        raise HTTPException(status_code=404, detail=traceback.format_exc())
