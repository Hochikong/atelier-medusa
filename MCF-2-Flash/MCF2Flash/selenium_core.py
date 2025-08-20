# file: sb_driver.py
import os
import shutil
import tempfile
import time
from typing import Optional

from seleniumbase import Driver


class SBWrapper:
    """
    非上下文管理器用法：
        wrapper = SBWrapper(...)
        driver  = wrapper.driver
        ...
        wrapper.dispose()
    """

    def __init__(
        self,
        *,
        browser_path: Optional[str] = None,
        proxy: Optional[str] = None,
        extension_zip: Optional[str] = None,
        user_data_dir: Optional[str] = None,
        user_agent: Optional[str] = None,
        browser: str = "chrome",
        uc: bool = True,
        **sb_kwargs,
    ):
        self._ensure_user_data_dir(user_data_dir)

        # 构造 SeleniumBase Driver 参数
        sb_options = {
            "browser": browser,
            "uc": uc,
            "headless": False,
            "binary_location": browser_path,
            "user_data_dir": user_data_dir or self._tmp_user_dir,
            "extension_zip": extension_zip,
            "proxy": proxy,
            "agent": user_agent,
            **sb_kwargs,
        }

        # 创建 Driver
        self.driver = Driver(**sb_options)

    # ------------------------------------------------------------------ #
    # 资源释放
    # ------------------------------------------------------------------ #
    def dispose(self) -> None:
        """关闭浏览器并清理临时用户数据目录"""
        try:
            self.driver.quit()
        finally:
            if self._tmp_user_dir and os.path.isdir(self._tmp_user_dir):
                shutil.rmtree(self._tmp_user_dir, ignore_errors=True)

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _ensure_user_data_dir(self, user_data_dir: Optional[str]) -> None:
        if user_data_dir:
            os.makedirs(user_data_dir, exist_ok=True)
            self._tmp_user_dir = None
        else:
            self._tmp_user_dir = tempfile.mkdtemp(prefix="sb_user_data_")


# ---------------------------------------------------------------------- #
# DEMO（非上下文管理器）
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    wrapper = SBWrapper(
        browser_path="C:\Program Files\Google\Chrome\Application\chrome.exe",
        proxy="socks5://127.0.0.1:5082",
        # extension_zip="/tmp/my_ext.zip",
        user_data_dir=r"C:\Users\ckhoi\PycharmProjects\atelier-medusa\tmp\ud",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
        uc = False

    )
    driver = wrapper.driver
    driver.get("https://ipinfo.io")
    time.sleep(20)
    wrapper.dispose()
