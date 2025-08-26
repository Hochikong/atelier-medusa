import os
import sys
import pathlib
import traceback

import pandas as pd
from typing import Any, List, Union
from seleniumbase import Driver, SB
from sqlalchemy import text

t = pathlib.Path(__file__).parent.resolve()
sys.path.append("..")
sys.path.append(str(t))
from MCF2Flash.commons.v2_abstract_extension import TaskListV2DataForExtensions, AbstractExtensionMCFV2
from MCF2Flash.commons.file_io import yaml_loader
from MCF2Flash.commons.udao import UniversalDAO
from MCF2Flash.commons.net_io import SimpleRedis
from MCF2Flash.mcf_2f.extension_mgr import ExtLoader
from MCF2Flash.mcf_2f.selenium_core import SBOmniWrapper


class MCF2FlashCore(object):
    def __init__(self, logger: Any, main_config_path: str):
        self.logger = logger

        if os.path.exists(main_config_path) and os.path.isfile(main_config_path):
            self.config: dict = yaml_loader(main_config_path, encoding='utf-8')
        else:
            raise FileNotFoundError(main_config_path)
        self.sb_manager = None
        self.sb: SB = None
        self.driver: Driver = None

        # 初始化日志和截图等目录
        self.download_dir = self.config['Common']['target_save_dir']
        os.makedirs(self.download_dir, exist_ok=True)
        self.log_dir = self.config['Logging']['logfile_dir']
        os.makedirs(self.log_dir, exist_ok=True)
        self.screenshot_dir = self.config['Logging']['screenshots']
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.plugin_logs_dir = self.config['Extensions']['plugin_logs_dir']
        os.makedirs(self.plugin_logs_dir, exist_ok=True)

        # 插件相关
        self.extension_config = self.config['Extensions']
        self.extension_ns = self.extension_config['namespace']
        self.extension_loader = ExtLoader(self.extension_ns, invoke_on_load=True)
        if len(self.extension_loader.extensions()) == 0:
            logger.warning("No MCFv2 extensions loaded!")
        self.extension_template_path = {ext_n: ext.get('extension_param_template_path', None) for ext_n, ext in
                                        self.extension_config['ByExtensions'].items()}
        self.dynamic_load_from = {ext_n: ext.get('dynamic_load_from', None) for ext_n, ext in
                                  self.extension_config['ByExtensions'].items()}

        self.running_lock = False

    def init_browser(self):
        if self.sb_manager is None:
            self.sb_manager = SBOmniWrapper(**self.config['Selenium'])
            self.sb = self.sb_manager.sb
            self.driver = self.sb_manager.driver
        else:
            self.logger.warning("Browser already initialized!")

    def dispose(self):
        if self.sb_manager is not None:
            self.sb_manager.dispose()
        self.sb = None
        self.driver = None
        self.sb_manager = None

    def run_driver(self, extensions: Union[List[str], str] = None) -> Any:
        ext_mgr = self.extension_loader
        sb_manger = self.sb_manager
        if isinstance(extensions, str):
            done, msg = ext_mgr.call(extensions, "prepare", sb_manger, self.config)
            if not done:
                self.logger.error(msg)
                raise Exception(msg)
            else:
                self.logger.info(msg)
            done, msg = ext_mgr.call(extensions, "handle")
            if not done:
                self.logger.error(msg)
                raise Exception(msg)
            else:
                self.logger.info(msg)
            result = ext_mgr.call(extensions, "get_plugin_return")
            if result:
                self.logger.info("Plugin return values:")
                self.logger.info(result)
                return result
            else:
                self.logger.warning("No plugin return value found!")
                return None
        elif isinstance(extensions, list):
            results_by_ext = {}
            unique_extensions = list(set(extensions))
            for ext in unique_extensions:
                done, msg = ext_mgr.call(ext, "prepare", sb_manger, self.config)
                if not done:
                    self.logger.error(msg)
                    raise Exception(msg)
                else:
                    self.logger.info(msg)
                done, msg = ext_mgr.call(ext, "handle")
                if not done:
                    self.logger.error(msg)
                    raise Exception(msg)
                else:
                    self.logger.info(msg)
                result = ext_mgr.call(ext, "get_plugin_return")
                if result:
                    self.logger.info(f"Plugin {ext} return values:")
                    self.logger.info(result)
                    results_by_ext[ext] = result
                else:
                    self.logger.warning(f"No plugin return value found for {ext}!")
                    results_by_ext[ext] = None
            return results_by_ext

    def run_tasks_in_db_not_done(self, dao: UniversalDAO) -> Any:
        ext_mgr = self.extension_loader
        logger = self.logger
        extension_template_path = self.extension_template_path
        dynamic_load_from = self.dynamic_load_from

        if self.running_lock:
            logger.warning("Running tasks is locked! Skip this job for now")
            return None

        if self.sb_manager is None:
            self.init_browser()

        logger.info("连接到数据库")
        dao.connect()
        not_done_tasks: pd.DataFrame = pd.read_sql(
            "select * from collector_rest.tasks_list_v2 tl where task_status = 3",
            dao.session.bind)
        if 'extra_content' not in not_done_tasks.columns:
            not_done_tasks['extra_content'] = None
        not_done_tasks = not_done_tasks[['id', 'created_at', 'updated_at', 'deleted_at', 'task_uid',
                                         'task_content', 'task_status', 'driver_info',
                                         'download_dir', 'extra_content']]
        if len(not_done_tasks) == 0:
            dao.disconnect()
            logger.info("No tasks to run!")
            return None
        else:
            logger.info(f"Found {len(not_done_tasks)} tasks to run!")
            dao.disconnect()
            self.running_lock = True
            try:
                tasks_by_driver = {}
                for driver in not_done_tasks['driver_info'].unique():
                    driver_tasks = not_done_tasks[not_done_tasks['driver_info'] == driver]
                    tasks_by_driver[driver] = driver_tasks

                valid_drivers = [drn for drn in tasks_by_driver if drn.startswith(self.extension_ns)]

                all_done_jobs = []

                for drn in valid_drivers:
                    ext_name = drn.split(':')[-1]
                    extension: AbstractExtensionMCFV2 = ext_mgr[ext_name]
                    rows: pd.DataFrame = tasks_by_driver[drn]
                    no_download_dir = rows[rows['download_dir'].isnull()].copy()
                    with_download_dir = rows[rows['download_dir'].notnull()].copy()

                    if len(no_download_dir) > 0:
                        logger.info("开始执行无专门指定下载目录的零散取数任务")
                        tasks_list = TaskListV2DataForExtensions.from_pandas(no_download_dir)
                        logger.info("调用插件解析队列任务")
                        tasks_list_template = extension.parse_tasklist_to_redis(
                            yaml_loader(extension_template_path[ext_name]),
                            tasks_list)
                        redis_client = SimpleRedis(dynamic_load_from[ext_name])
                        redis_client.set(ext_name, tasks_list_template)
                        logger.info("任务已保存至Redis")

                        r = self.run_driver(ext_name)
                        done_tasks = r.get('done_tasks', [])
                        if len(done_tasks) > 0:
                            all_done_jobs.extend(done_tasks)
                        logger.info("零散任务执行完毕\n")

                    if len(with_download_dir):
                        logger.info("开始执行有指定下载目录的零散取数任务")
                        for down_dir in with_download_dir['download_dir'].unique():
                            tasks_list = TaskListV2DataForExtensions.from_pandas(
                                with_download_dir[with_download_dir['download_dir'] == down_dir])
                            tasks_list_template = extension.parse_tasklist_to_redis(
                                yaml_loader(extension_template_path[ext_name]),
                                tasks_list)
                            redis_client = SimpleRedis(dynamic_load_from[ext_name])
                            redis_client.set(ext_name, tasks_list_template)
                            logger.info("任务已保存至Redis")
                            r = self.run_driver(ext_name)
                            done_tasks = r.get('done_tasks', [])
                            if len(done_tasks) > 0:
                                all_done_jobs.extend(done_tasks)
                            logger.info(f"指定下载目录为{down_dir}的任务执行完毕\n")

                    logger.info(f"所有属于插件{drn}的任务执行完毕\n")
                logger.info(f"所有任务执行完毕")

                done_content_stmt = ",".join([f"'{task_uid}'" for task_uid in all_done_jobs])
                sql = f"update collector_rest.tasks_list_v2 set task_status = 1 where task_content in ({done_content_stmt})"
                dao.connect()
                dao.session.execute(text(sql))
                dao.session.commit()
                dao.disconnect()
            except Exception as _:
                logger.error(traceback.format_exc())
            finally:
                dao.disconnect()
                self.running_lock = False
                return True
