import uuid

from djsplugins.MCF2f.driver_router import get_router_output_v2
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

import MCF2Flash.repository.defined_repositories as dr
from MCF2Flash.celery_misc.mcf_v2_tasks import init_browser as ib, dispose_browser as db, run_tasks_not_done
from MCF2Flash.domains.defined_domains import SingleTaskReceive, BulkTasksReceive, TaskRowCreate
from MCF2Flash.fastapi_depends import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/mcf/v2/init_browser", tags=['MCF2Flash'])
def init_browser():
    task = ib.delay()
    return {"celery_task_id": task.id}


@router.get("/mcf/v2/dispose_browser", tags=['MCF2Flash'])
def dispose_browser():
    task = db.delay()
    return {"celery_task_id": task.id}


@router.post("/mcf/v2/tasks/single/", tags=['tasks'])
def receive_task(task: SingleTaskReceive, db: Session = Depends(get_db)):
    total_status = False
    logger.info(f"Received task: {task.url}")
    driver_info = get_router_output_v2(task.url)
    for info in driver_info:
        created_task = TaskRowCreate(task_uid=str(uuid.uuid4()), task_content=task.url, task_status=3,
                                     driver_info=info['driver'])
        status = dr.create_task(db, created_task)
        total_status = status
    return {'status': total_status}


@router.post("/mcf/v2/tasks/bulk/", tags=['tasks'])
def receive_tasks(tasks: BulkTasksReceive, db: Session = Depends(get_db)):
    total_status = False
    params = tasks.params
    for url in tasks.urls:
        driver_info = get_router_output_v2(url)
        for info in driver_info:
            created_task = TaskRowCreate(task_uid=str(uuid.uuid4()), task_content=url, task_status=3,
                                         driver_info=info['driver'],
                                         download_dir=params.get('download_child_dir', None))
            status = dr.create_task(db, created_task)
            total_status = status
    return {'status': total_status}


@router.get('/mcf/v2/tasks/{uid}', tags=['tasks'])
def get_single_task(uid: str, db: Session = Depends(get_db)):
    try:
        return dr.get_task_by_uid(db, uid)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Item not found")


@router.get('/mcf/v2/tasks/status/', tags=['tasks'])
def get_tasks_by_status(code: int, db: Session = Depends(get_db)):
    return dr.get_tasks_by_status(db, code)

@router.post('/mcf/v2/tasks/run_not_done', tags=['tasks'])
def run_not_done():
    task = run_tasks_not_done.delay()
    return {"celery_task_id": task.id}