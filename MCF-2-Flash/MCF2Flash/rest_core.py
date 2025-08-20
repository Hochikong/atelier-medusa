import logging

from celery.result import AsyncResult
from fastapi import FastAPI

from MCF2Flash.celery_misc.tasks import add, celery_app, must_failed

# from uvicorn.server import logger
logger = logging.getLogger(__file__)
from MCF2Flash.controllers import testing

app = FastAPI()
app.include_router(testing.router)


@app.post("/add")
def submit_add(x: int, y: int):
    task = add.delay(x, y)
    return {"celery_task_id": task.id}


@app.post("/must_failed")
def submit_add(x: int, y: int):
    task = must_failed.delay(x, y)
    return {"celery_task_id": task.id}


@app.get("/async_result/{task_id}")
def get_result(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None
    }


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI + Celery Demo"}


# @app.get("/async_task/{task_id}")
# def get_task(task_id: str):
#     task_result = AsyncResult(task_id)
#     return {
#         "task_id": task_id,
#         "status": task_result.state,
#         "result": task_result.result
#     }


# 可选：本地调试入口
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "testing_service.main:app"
    )
