import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

import MCF2Flash.repository.defined_repositories as dr
from MCF2Flash.celery_misc.mcf_v2_tasks import init_browser as ib, dispose_browser as db, run_tasks_not_done
from MCF2Flash.domains.defined_domains import SingleTaskReceive, BulkTasksReceive, TaskRowCreate, \
    SingleTaskReceiveSpecial
from MCF2Flash.fastapi_depends import SessionLocal, get_namespace_common, get_driver_mgmt
from MCF2Flash.commons.v2_abstract_extension import TaskListV2DataForExtensions, AbstractExtensionMCFV2

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


@router.post("/mcf/v2/tasks/single/special", tags=['tasks'])
def receive_task_special(task: SingleTaskReceiveSpecial, db: Session = Depends(get_db)):
    """
    适用于特殊任务的一次性提交

    :param task:
    :param db:
    :return:
    """
    logger.info(f"Received task: {task.url}")

    exists_tasks = dr.get_same_special_tasks(db, task)
    exists_tasks = [i.to_dict() for i in exists_tasks]

    NO_SAME_TASKS = True
    if len(exists_tasks) > 0:
        exists_tasks_df = pd.DataFrame(exists_tasks)
        tl = TaskListV2DataForExtensions.from_pandas(exists_tasks_df)
        current_task = TaskListV2DataForExtensions(task_uid=str(uuid.uuid4()),
                                                   task_content=task.url,
                                                   task_status=3,
                                                   driver_info=task.driver,
                                                   download_dir=None,
                                                   extra_content=task.extra_content,
                                                   _namespace=task.driver.split(":")[0],
                                                   _driver_name=task.driver.split(":")[1])

        extension: AbstractExtensionMCFV2 = get_driver_mgmt().extension_loader[current_task._driver_name]
        for exists_task in tl:
            if extension.task_equal(current_task, exists_task):
                NO_SAME_TASKS = False
                break
    else:
        NO_SAME_TASKS = True

    if NO_SAME_TASKS:
        created_task = TaskRowCreate(task_uid=str(uuid.uuid4()), task_content=task.url, task_status=3,
                                     driver_info=task.driver, extra_content=task.extra_content)
        status = dr.create_task(db, created_task)
        total_status = status
        return {'status': total_status}
    else:
        return {'status': False, "msg": f"任务: ({task}) 已存在，拒绝再次添加特殊任务"}


@router.post("/mcf/v2/tasks/single/", tags=['tasks'])
def receive_task(task: SingleTaskReceive, db: Session = Depends(get_db)):
    """
    常规批量任务单个发送

    :param task:
    :param db:
    :return:
    """
    logger.info(f"Received task: {task.url}")
    driver_info = get_namespace_common().infer_driver(task.url)

    for info in driver_info:
        driver_full_name = info['driver']

        exists_tasks = dr.get_tasks_by_content(db, task.url, driver_full_name)
        exists_tasks = [i.to_dict() for i in exists_tasks]

        NO_SAME_TASKS = True
        if len(exists_tasks) > 0:
            exists_tasks_df = pd.DataFrame(exists_tasks)
            tl = TaskListV2DataForExtensions.from_pandas(exists_tasks_df)
            current_task = TaskListV2DataForExtensions(task_uid=str(uuid.uuid4()),
                                                       task_content=task.url,
                                                       task_status=3,
                                                       driver_info=driver_full_name,
                                                       download_dir=None,
                                                       extra_content=None,
                                                       _namespace=driver_full_name.split(":")[0],
                                                       _driver_name=driver_full_name.split(":")[1])

            extension: AbstractExtensionMCFV2 = get_driver_mgmt().extension_loader[current_task._driver_name]
            for exists_task in tl:
                if extension.task_equal(current_task, exists_task):
                    NO_SAME_TASKS = False
                    break
        else:
            NO_SAME_TASKS = True

        if NO_SAME_TASKS:
            created_task = TaskRowCreate(task_uid=str(uuid.uuid4()), task_content=task.url, task_status=3,
                                         driver_info=driver_full_name)
            status = dr.create_task(db, created_task)
            total_status = status
            return {'status': total_status}
        else:
            return {'status': False, "msg": f"任务: ({task.url}) 已存在，拒绝再次添加Single任务"}


@router.post("/mcf/v2/tasks/bulk/", tags=['tasks'])
def receive_tasks_bulk(tasks: BulkTasksReceive, db: Session = Depends(get_db)):
    """
    常规批量任务批量发送

    :param tasks:
    :param db:
    :return:
    """
    params = tasks.params

    add_urls = []
    urls_with_status = []

    for url in tasks.urls:
        logger.warning(f"Received task: {url}")
        driver_info = get_namespace_common().infer_driver(url)
        logger.warning(driver_info)
        for info in driver_info:
            driver_full_name = info['driver']

            exists_tasks = dr.get_tasks_by_content(db, url, driver_full_name)
            exists_tasks = [i.to_dict() for i in exists_tasks]

            NO_SAME_TASKS = True
            if len(exists_tasks) > 0:
                exists_tasks_df = pd.DataFrame(exists_tasks)
                tl = TaskListV2DataForExtensions.from_pandas(exists_tasks_df)
                current_task = TaskListV2DataForExtensions(task_uid=str(uuid.uuid4()),
                                                           task_content=url,
                                                           task_status=3,
                                                           driver_info=driver_full_name,
                                                           download_dir=None,
                                                           extra_content=None,
                                                           _namespace=driver_full_name.split(":")[0],
                                                           _driver_name=driver_full_name.split(":")[1])

                extension: AbstractExtensionMCFV2 = get_driver_mgmt().extension_loader[current_task._driver_name]
                for exists_task in tl:
                    if extension.task_equal(current_task, exists_task):
                        NO_SAME_TASKS = False
                        break
            else:
                NO_SAME_TASKS = True

            if NO_SAME_TASKS:
                created_task = TaskRowCreate(task_uid=str(uuid.uuid4()), task_content=url, task_status=3,
                                             driver_info=driver_full_name,
                                             download_dir=params.get('download_child_dir', None))
                status = dr.create_task(db, created_task)
                add_urls.append(url)
                urls_with_status.append({'url': url, 'status': status})
            else:
                urls_with_status.append({'url': url, 'status': False, "msg": f"任务: ({url}) 已存在，拒绝再次添加为Bulk任务成员"})

    return {'status': urls_with_status}


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
