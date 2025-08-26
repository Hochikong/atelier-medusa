import datetime

from sqlalchemy.orm import Session
from typing import List
from MCF2Flash.entities.defined_entities import TasksListV2
import MCF2Flash.domains.defined_domains as domains


def get_task_by_uid(db: Session, uuid: str) -> TasksListV2:
    return db.query(TasksListV2).filter(TasksListV2.task_uid == uuid).one()


def get_tasks_by_status(db: Session, status: int) -> List[TasksListV2]:
    return db.query(TasksListV2).filter(TasksListV2.task_status == status).all()


def get_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[TasksListV2]:
    return db.query(TasksListV2).offset(skip).limit(limit).all()


def create_task(db: Session, task_params: domains.TaskRowCreate) -> bool:
    new_task = TasksListV2(**task_params.model_dump(), deleted_at=datetime.datetime(2077, 1, 1, 8, 0, 0, 0))
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return True


def update_task_status(db: Session, uuid: str, status: int) -> bool:
    task = get_task_by_uid(db, uuid)
    task.task_status = status
    db.commit()
    db.refresh(task)
    return True
