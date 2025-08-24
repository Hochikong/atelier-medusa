import os
import sys
import pathlib
from typing import Any
from seleniumbase import Driver, SB

t = pathlib.Path(__file__).parent.resolve()
sys.path.append("..")
sys.path.append(str(t))

from commons.file_io import yaml_loader
from mcf_2f.extension_mgr import ExtLoader
from mcf_2f.selenium_core import SBOmniWrapper


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

    def init_browser(self):
        self.sb_manager = SBOmniWrapper(**self.config['Selenium'])
        self.sb = self.sb_manager.sb
        self.driver = self.sb_manager.driver

    def dispose(self):
        self.sb_manager.dispose()
        self.sb = None
        self.driver = None
        self.sb_manager = None

    def run_driver(self, extensions: str = None) -> Any:
        ext_mgr = self.extension_loader
        sb_manger = self.sb_manager
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
