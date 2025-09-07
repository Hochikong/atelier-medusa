import logging

from celery.result import AsyncResult
from fastapi import FastAPI
from MCF2Flash.loguru_setup import loguru_setup
from MCF2Flash.celery_core import celery_app
from MCF2Flash.fastapi_depends import engine
from MCF2Flash.controllers import test_view, mcf_v2_view
from MCF2Flash.fastapi_depends import Dec_Base
loguru_setup('fast_api')
logger = logging.getLogger(__file__)

# 如果存在，则跳过
Dec_Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(test_view.router)
app.include_router(mcf_v2_view.router)


@app.get("/async_result/{task_id}", tags=['System'])
def get_result(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    logger.info(f"FASTAPI: {res.result}")
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None
    }


@app.get("/")
def read_root():
    return {"message": "Welcome to MCF 2.0 Flash"}


# 可选：本地调试入口
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "testing_service.main:app"
    )
