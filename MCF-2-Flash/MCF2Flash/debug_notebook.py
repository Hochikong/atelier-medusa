"""
调试脚本，用于在 Jupyter Notebook 或 IPython 中快速初始化 MCF2FlashCore 实例
"""

import os
from loguru import logger
from mcf_2f.mcf_2f_core import MCF2FlashCore


def create_mcf_core(config_path=None):
    """
    创建 MCF2FlashCore 实例用于调试
    
    Args:
        config_path (str, optional): 配置文件路径。如果未提供，将尝试使用默认路径
        
    Returns:
        MCF2FlashCore: 初始化的 MCF2FlashCore 实例
    """
    # 如果没有提供配置文件路径，则使用默认示例配置
    if config_path is None:
        # 尝试几种可能的配置文件路径
        possible_paths = [
            r"C:\Users\ckhoi\PycharmProjects\atelier-medusa\MCF-2-Flash\configs_example\win_main_config.yaml",
            "./configs_example/win_main_config.yaml",
            "../configs_example/win_main_config.yaml",
            "./configs/win_main_config.yaml"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break

        if config_path is None:
            raise FileNotFoundError("无法找到配置文件，请提供有效的配置文件路径")

    # 创建并返回 MCF2FlashCore 实例
    core = MCF2FlashCore(logger, config_path)
    return core


# 使用示例:
# core = create_mcf_core()
# core.init_browser()

if __name__ == "__main__":
    # 当直接运行此脚本时，创建核心实例
    cfg_path = r"xxx"

    core = create_mcf_core(cfg_path)
    print("MCF2FlashCore 实例创建成功!")
    print(f"配置文件路径: {core.config}")
    core.init_browser()
    driver = core.driver
    ext_mgr = core.extension_loader

    # extensions = 'xxx'
    # done, msg = ext_mgr.call(extensions, "prepare", core.sb_manager, core.config)
    # plugin = ext_mgr[extensions]

    # 生成请求参数用于special
    # print(json.dumps(json.dumps(b, ensure_ascii=False)))