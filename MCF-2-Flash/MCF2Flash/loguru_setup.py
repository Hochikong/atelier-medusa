import logging
import os

from loguru import logger

from MCF2Flash.app_config import MCF_CELERY_LOG_DIR, DEBUG_MODE


def loguru_setup(filename_prefix: str = "celery-worker", level: str = "INFO"):
    """filename 只给文件名即可，目录固定为 MCF_CELERY_LOG_DIR"""
    filename = '%s_{time}.log' % filename_prefix
    os.makedirs(MCF_CELERY_LOG_DIR, exist_ok=True)
    if not DEBUG_MODE:
        logger.remove()
    logger.add(
        os.path.join(MCF_CELERY_LOG_DIR, filename),
        rotation="50 MB",
        retention="7 days",
        level=level,
        format='[{time:YYYY-MM-DD} {time:HH:mm:ss}][{file}:{line}][{level}] -> {message}',
        enqueue=True,
        backtrace=False,
    )

    # 桥接到标准 logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            logger.opt(depth=6, exception=record.exc_info).log(
                record.levelname, record.getMessage()
            )

    root = logging.getLogger()
    if not any(isinstance(h, InterceptHandler) for h in root.handlers):
        root.handlers[:] = [InterceptHandler()]
        root.setLevel(logging.DEBUG)
