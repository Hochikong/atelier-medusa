import atexit
import json
import readline

from pathlib import Path
from typing import List, Dict, Any
from mcf_2f.cmd_parser import MCF2ShellParser
from mcf_2f.mcf_2f_core import MCF2FlashCore


class MiniREPL:
    HIST_FILE = Path.home() / '.mini_repl_history.json'
    print(f"History saved to {HIST_FILE}")
    MAX_PERSISTENT = 10  # 重启后保留条数

    intro = "| Welcome to use MCF 2.0 Flash REPL!\n| Version: 0.0.1 - 20250824"
    prompt = "MCFv2 >>>"

    def __init__(self, obj: MCF2FlashCore):
        self._in_memory: List[str] = []  # 本次会话全部历史
        self._load_history()
        self.managed_objects = {}
        atexit.register(self._save_history)
        self.managed_objects['mcf_core'] = obj
        self.shell_parser = MCF2ShellParser(logger, self.managed_objects['mcf_core'])

    def inject_managed_instance(self, name: str, obj: Any):
        self.managed_objects[name] = obj

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
        total = [readline.get_history_item(i) for i in
                 range(1, readline.get_current_history_length() + 1)] + self._in_memory
        with open(self.HIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(total[-self.MAX_PERSISTENT:], f, ensure_ascii=False)

    # ─── 公开 API ────────────────────────────────────────────
    def run(self) -> None:
        """启动 REPL"""
        print(self.intro)
        while True:
            try:
                line = input(f'{self.prompt} ').rstrip()
                self._in_memory.append(line)  # 记录全部历史
                parsed = self.shell_parser.basic_parse(line)
                self.handle(parsed)
            except (KeyboardInterrupt, EOFError):
                print()
                break

    def handle(self, parsed: Dict[str, Any]) -> None:
        """子类可重写此钩子，实现真正业务"""
        if parsed['type'] == 'cmd':
            # print(f'[CMD] {parsed["cmd"]} -> {parsed["args"]}')
            r = self.shell_parser.cmd_shell_conditions(parsed)
            if r:
                if r == 'exit':
                    print('Bye')
                    exit(0)
                print(r)
        else:
            print("")
            # print(f'[EXPR] {parsed["raw"]}')


def add_basic_parser(parser):
    parser.add_argument('-c', '--cfg',
                        type=str, help="Configuration file path.", metavar="YAML FILE")
    parser.add_argument('-x', '--xdisplay',
                        help="是否启用headless模式，仅支持在linux下运行，可以配置文件中选择基于Xvfb或者VNC的后端",
                        action='store_true')
    parser.add_argument('-f', '--forward', help="通过noVNC转发本地xdisplay到浏览器", metavar="用于被外部访问的目标端口",
                        type=int)
    parser.add_argument('--all_notify', help="启用全部通知", action='store_true')


if __name__ == '__main__':
    import argparse
    from loguru import logger

    parser = argparse.ArgumentParser("MCFDataCollector Modular Scraper")
    add_basic_parser(parser)
    args = parser.parse_args()

    # repl = MiniREPL(MCF2FlashCore(logger, r"C:\Users\ckhoi\PycharmProjects\atelier-medusa\MCF-2-Flash\configs\win_main_config.yaml"))
    repl = MiniREPL(MCF2FlashCore(logger, args.cfg))
    repl.run()
