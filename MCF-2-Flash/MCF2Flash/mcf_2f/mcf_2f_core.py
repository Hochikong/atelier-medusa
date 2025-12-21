import os
import subprocess
import sys
import pathlib
import traceback
from time import sleep

import pandas as pd
from typing import Any, List, Union

import psutil
from seleniumbase import Driver, SB
from seleniumbase.core import browser_launcher
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


class DriverMgmt(object):
    def __init__(self, main_config_path: str):
        if os.path.exists(main_config_path) and os.path.isfile(main_config_path):
            self.config: dict = yaml_loader(main_config_path, encoding='utf-8')
        else:
            raise FileNotFoundError(main_config_path)

        self.extension_config = self.config['Extensions']
        self.extension_ns = self.extension_config['namespace']
        self.extension_loader = ExtLoader(self.extension_ns, invoke_on_load=True)


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

        # 指定chromedriver path
        self.driver_path = self.config.get('Environment', {}).get('chrome_driver_path', None)
        if self.driver_path:
            browser_launcher.override_driver_dir(self.driver_path)

        # 运行环境
        self.xvfb = self.config.get('Selenium', {}).get('xvfb', False)
        self.xvfb_display: int = -1
        self.vnc_port = self.config.get('Environment', {}).get('vnc_port', 5911)
        self.novnc_port = self.config.get('Environment', {}).get('novnc_port', 9101)
        self.x11vnc_proc = None
        self.novnc_proc = None

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
            if self.xvfb:
                if self.sb_manager.sb.xvfb:
                    # 通过启用SB的xvfb参数来实现xvfb，然后通过他的自定义的pyvirtualdisplay来获取xvfb的display编号，从而实现vnc转发
                    self.xvfb_display = int(self.sb_manager.sb._xvfb_display.new_display_var.replace(":", ""))
                    self.start_novnc()
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

        self.stop_novnc()

    def stop_novnc(self):
        if self.novnc_proc:
            pid = self.novnc_proc.pid
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            self.novnc_proc.terminate()

        if self.x11vnc_proc:
            pid = self.x11vnc_proc.pid
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            self.x11vnc_proc.terminate()

    def start_novnc(self) -> bool:
        logger = self.logger
        vnc_port = self.vnc_port
        forward_port = self.novnc_port
        if os.name == 'posix' and self.xvfb:
            # 默认PyVirtualDisplay实现
            try:
                # kill掉有相同rfbport的xvnc进程
                vnc_processes = []
                for proc in psutil.process_iter():
                    try:
                        if f'-rfbport {vnc_port}' in ' '.join(proc.cmdline()):
                            print(proc.cmdline())
                            vnc_processes.append(proc)
                    except Exception:
                        logger.warning(f"获取进程信息失败: {proc.pid}")
                        logger.warning(traceback.format_exc())
                for i in vnc_processes:
                    i.kill()
                    logger.info(f"清除抢占xvnc端口: {vnc_port} 的进程")
                sleep(1)

                logger.info(f"启动x11vnc服务，转发本地xvfb display:{self.xvfb_display}至vnc端口{vnc_port}")
                self.x11vnc_proc = subprocess.Popen(
                    f"x11vnc -display :{self.xvfb_display} -forever -shared -nopw -rfbport {vnc_port}",
                    shell=True)

                logger.info(f"启动novnc服务，转发本地vnc端口{vnc_port}至novnc端口{forward_port}")
                self.novnc_proc = subprocess.Popen(
                    f"websockify --web=/usr/share/novnc {forward_port} localhost:{vnc_port}",
                    shell=True)
                return True
            except Exception as _:
                logger.error(traceback.format_exc())
                return False
        else:
            return False

    def _run_driver(self, extensions: Union[List[str], str] = None) -> Any:
        """
        这个函数在web部署时不允许被直接调用

        :param extensions:
        :return:
        """
        ext_mgr = self.extension_loader
        sb_manager = self.sb_manager
        if isinstance(extensions, str):
            done, msg = ext_mgr.call(extensions, "prepare", sb_manager, self.config)
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
                done, msg = ext_mgr.call(ext, "prepare", sb_manager, self.config)
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
            "select * from tasks_list_v2 tl where task_status = 3",
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

                    # 是否拥有指定的子下载目录
                    no_download_dir = rows[rows['download_dir'].isnull()].copy()
                    with_download_dir = rows[rows['download_dir'].notnull()].copy()

                    if extension.can_merge_multiple_to_one_batch():
                        if len(no_download_dir) > 0:
                            logger.info("开始执行 可合并子任务-无专门指定下载目录 的零散取数任务")
                            tasks_list = TaskListV2DataForExtensions.from_pandas(no_download_dir)
                            logger.info("调用插件解析队列任务")
                            tasks_list_template = extension.parse_tasklist_to_redis(
                                yaml_loader(extension_template_path[ext_name]),
                                tasks_list)
                            redis_client = SimpleRedis(dynamic_load_from[ext_name])
                            redis_client.set(ext_name, tasks_list_template)
                            logger.info("任务已保存至Redis")

                            r = self._run_driver(ext_name)
                            done_tasks = r.get('done_tasks', [])
                            if len(done_tasks) > 0:
                                all_done_jobs.extend(done_tasks)
                            logger.info("零散任务执行完毕\n")

                        if len(with_download_dir) > 0:
                            logger.info("开始执行 可合并子任务-有指定下载目录 的零散取数任务")
                            for down_dir in with_download_dir['download_dir'].unique():
                                tasks_list = TaskListV2DataForExtensions.from_pandas(
                                    with_download_dir[with_download_dir['download_dir'] == down_dir])
                                tasks_list_template = extension.parse_tasklist_to_redis(
                                    yaml_loader(extension_template_path[ext_name]),
                                    tasks_list)
                                redis_client = SimpleRedis(dynamic_load_from[ext_name])
                                redis_client.set(ext_name, tasks_list_template)
                                logger.info("任务已保存至Redis")
                                r = self._run_driver(ext_name)
                                done_tasks = r.get('done_tasks', [])
                                if len(done_tasks) > 0:
                                    all_done_jobs.extend(done_tasks)
                                logger.info(f"指定下载目录为{down_dir}的任务执行完毕\n")
                    else:
                        if len(no_download_dir) > 0:
                            logger.info("开始执行 不可合并子任务-无专门指定下载目录 的零散取数任务")
                            tasks_list = TaskListV2DataForExtensions.from_pandas(no_download_dir)
                            for task in tasks_list:
                                # 不可合并任务使用task_uid来标记任务完成情况
                                task_uid = task.task_uid
                                logger.info("调用插件解析队列任务")
                                tasks_list_template = extension.parse_tasklist_to_redis(
                                    yaml_loader(extension_template_path[ext_name]),
                                    [task])
                                redis_client = SimpleRedis(dynamic_load_from[ext_name])
                                redis_client.set(ext_name, tasks_list_template)
                                logger.info("任务已保存至Redis")

                                r = self._run_driver(ext_name)
                                done_tasks = r.get('done_tasks', [])
                                if len(done_tasks) > 0:
                                    all_done_jobs.append(task_uid)
                                logger.info(f"零散任务 {task} 执行完毕\n")
                        if len(with_download_dir) > 0:
                            logger.info("开始执行 不可合并子任务-有指定下载目录 的零散取数任务")
                            for down_dir in with_download_dir['download_dir'].unique():
                                tasks_list = TaskListV2DataForExtensions.from_pandas(
                                    with_download_dir[with_download_dir['download_dir'] == down_dir])
                                for task in tasks_list:
                                    task_uid = task.task_uid
                                    tasks_list_template = extension.parse_tasklist_to_redis(
                                        yaml_loader(extension_template_path[ext_name]),
                                        [task])
                                    redis_client = SimpleRedis(dynamic_load_from[ext_name])
                                    redis_client.set(ext_name, tasks_list_template)
                                    logger.info("任务已保存至Redis")
                                    r = self._run_driver(ext_name)
                                    done_tasks = r.get('done_tasks', [])
                                    if len(done_tasks) > 0:
                                        all_done_jobs.append(task_uid)
                                    logger.info(f"指定下载目录为{down_dir}的{task}任务执行完毕\n")

                    logger.info(f"所有属于插件{drn}的任务执行完毕\n")
                logger.info(f"所有任务执行完毕")

                done_content_stmt = ",".join([f"'{task_uid}'" for task_uid in all_done_jobs])
                sql = f"update tasks_list_v2 set task_status = 1 where task_content in ({done_content_stmt}) or task_uid in ({done_content_stmt})"
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
