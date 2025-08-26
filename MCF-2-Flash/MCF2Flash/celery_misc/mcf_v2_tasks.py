import pathlib
import sys
import logging

t = pathlib.Path(__file__).parent.resolve()
sys.path.append("..")
sys.path.append(str(t))
from MCF2Flash.commons.udao import UniversalDAO
from MCF2Flash.celery_core import celery_app, get_mcf
from MCF2Flash.app_config import MCF2F_DB_URL

logger = logging.getLogger(__name__)


@celery_app.task(name="init_browser")
def init_browser():
    mcf = get_mcf()
    mcf.init_browser()
    return True


@celery_app.task(name="dispose_browser")
def dispose_browser():
    mcf = get_mcf()
    mcf.dispose()
    return True


@celery_app.task(name="run_tasks_not_done")
def run_tasks_not_done():
    mcf = get_mcf()
    dao = UniversalDAO(MCF2F_DB_URL, logger)
    mcf.run_tasks_in_db_not_done(dao)
    return True
