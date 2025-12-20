import traceback
from typing import Dict, Any
import shlex
from MCF2Flash.mcf_2f.mcf_2f_core import MCF2FlashCore


class MCF2ShellParser(object):
    def __init__(self, logger: any, managed_obj: MCF2FlashCore):
        self.managed_obj = managed_obj
        self.logger = logger

    @staticmethod
    def basic_parse(line: str) -> Dict[str, Any]:
        """把原始输入解析成结构化字典"""
        line = line.strip()
        if line.startswith('/'):
            # /开头的为系统指令
            cmd, *args = shlex.split(line[1:])
            return {'type': 'cmd', 'cmd': cmd, 'args': args}
        return {'type': 'expr', 'raw': line}

    def cmd_shell_conditions(self, parse_result: dict) -> Any:
        mcf = self.managed_obj
        logger = self.logger
        if parse_result['type'] == 'cmd':
            CMD = parse_result['cmd']
            if CMD == 'help' or CMD == 'h':
                print("Enter command without parameters to see how to use it.")
                print("Available commands: ")
                print("  /h or /help [command]    - Show help for a specific command")
                print("  /get_browser             - Init browser by configuration file")
                print("  /safe_check              - Check the browser status and visit a cloudflare protected website")
                print("  /run_extension           - Run a MCF v2 Extension, example: /run_extension XXX")
                print("  /exit                    - Exit shell")

            elif CMD == 'get_browser':
                print("Getting browser...")
                mcf.init_browser()
            elif CMD == 'safe_check':
                print("Checking browser...")
                print(f"Enable UC: {mcf.driver.is_uc_mode_active()}")
                print(f"Enable CDP: {mcf.driver.is_cdp_mode_active()}")
                print(f"Driver Connected: {mcf.driver.is_connected()}")
                mcf.sb.open('https://nowsecure.nl')
            elif CMD == 'run_extension':
                print("Running extension...")
                driver_name = parse_result['args'][0]
                try:
                    result = mcf._run_driver(driver_name)
                    print(result)
                except Exception as _:
                    print(traceback.format_exc())
            elif CMD == 'exit':
                print("Exiting...")
                if mcf:
                    mcf.dispose()
                return 'exit'
            else:
                print("Unknown command: " + CMD)
        else:
            return ""
