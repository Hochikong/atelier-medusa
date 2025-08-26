from typing import List
from pydantic import BaseModel

# pydantic model适用于view函数返回或者作为view函数的输入，如果要执行查询，需要转换为entity（即ORM对象）或者启用from_attributes

class SingleTaskReceive(BaseModel):
    url: str


class BulkTasksReceive(BaseModel):
    urls: List[str]
    params: dict


class TaskRowCreate(BaseModel):
    task_uid: str
    task_content: str
    task_status: int
    driver_info: str
    download_dir: str = None
    extra_content: str = None

    class Config:
        from_attributes = True