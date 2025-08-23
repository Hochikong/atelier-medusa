import atexit
import json
import os
import readline
import shlex
from pathlib import Path
from typing import List, Dict, Any

from commons.file_io import yaml_loader
from mcf_2f_cores.extension_mgr import ExtLoader
from mcf_2f_cores.selenium_core import SBOmniWrapper


class MiniREPL:
    HIST_FILE = Path.home() / '.mini_repl_history.json'
    print(HIST_FILE)
    MAX_PERSISTENT = 5  # 重启后保留条数

    def __init__(self):
        self._in_memory: List[str] = []  # 本次会话全部历史
        self._load_history()
        atexit.register(self._save_history)

    # ─── 内部工具 ────────────────────────────────────────────
    def _load_history(self) -> None:
        """把上次存的最近 N 条装入 readline"""
        try:
            with open(self.HIST_FILE, encoding='utf-8') as f:
                lines = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            lines = []
        for l in lines[-self.MAX_PERSISTENT:]:
            readline.add_history(l)

    def _save_history(self) -> None:
        """退出时持久化最近 N 条"""
        total = list(dict.fromkeys(
            [readline.get_history_item(i)
             for i in range(1, readline.get_current_history_length() + 1)]
            + self._in_memory
        ))
        with open(self.HIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(total[-self.MAX_PERSISTENT:], f, ensure_ascii=False)

    # ─── 公开 API ────────────────────────────────────────────
    @staticmethod
    def parse(line: str) -> Dict[str, Any]:
        """把原始输入解析成结构化字典"""
        line = line.strip()
        if line.startswith('/'):
            cmd, *args = shlex.split(line[1:])
            return {'type': 'cmd', 'cmd': cmd, 'args': args}
        return {'type': 'expr', 'raw': line}

    def run(self) -> None:
        """启动 REPL"""
        print('Mini-Python-REPL  (输入 exit / Ctrl-D 退出)')
        while True:
            try:
                line = input('>>> ').rstrip()
                if line in {'exit', 'quit'}:
                    break
                self._in_memory.append(line)  # 记录全部历史
                parsed = self.parse(line)
                self.handle(parsed)
            except (KeyboardInterrupt, EOFError):
                print()
                break

    def handle(self, parsed: Dict[str, Any]) -> None:
        """子类可重写此钩子，实现真正业务"""
        if parsed['type'] == 'cmd':
            print(f'[CMD] {parsed["cmd"]} -> {parsed["args"]}')
        else:
            print(f'[EXPR] {parsed["raw"]}')


class MCF2FlashCore(object):
    def __init__(self, logger: Any, main_config_path: str):
        self.logger = logger

        if os.path.exists(main_config_path) and os.path.isfile(main_config_path):
            self.config: dict = yaml_loader(main_config_path, encoding='utf-8')
        else:
            raise FileNotFoundError(main_config_path)
        self.sb_manager = None
        self.sb = None
        self.driver = None

        # 初始化日志和截图等目录
        self.download_dir = self.config['Common']['target_save_dir']
        os.makedirs(self.download_dir, exist_ok=True)
        self.log_dir = self.config['Logging']['logfile_dir']
        os.makedirs(self.log_dir, exist_ok=True)
        self.screenshot_dir = self.config['Common']['screenshots']
        os.makedirs(self.screenshot_dir, exist_ok=True)

        # 插件相关
        self.extension_config = self.config['Extensions']
        self.extension_ns = self.extension_config['namespace']
        self.extension_loader = ExtLoader(self.extension_ns, invoke_on_load=True)
        if len(self.extension_loader.extensions()) == 0:
            logger.waring("No MCFv2 extensions loaded!")

    def init_browser(self):
        self.sb_manager = SBOmniWrapper(**self.config['Selenium'])
        self.sb = self.sb_manager.sb
        self.driver = self.sb_manager.driver

    def dispose(self):
        self.sb_manager.dispose()
        self.sb = None
        self.driver = None
        self.sb_manager = None
