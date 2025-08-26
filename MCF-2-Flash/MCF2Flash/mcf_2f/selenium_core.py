import os
import shutil
import tempfile
import time
from typing import Optional

from seleniumbase import Driver
from seleniumbase import SB


class SBDriverWrapper:
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


class SBOmniWrapper:
    """
    对 SeleniumBase 的轻量包装，支持常用自定义启动参数，并暴露原生 Driver。
    使用示例：
        sb = SBWrapper(
            browser="chrome",
            binary_location="/opt/chrome/chrome",
            proxy_server="127.0.0.1:8080",
            extension_zip="/tmp/my_ext.zip",
            user_data_dir="/tmp/chrome_profile",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
        )
        sb.driver.get("https://example.com")
        sb.dispose()
    """

    def __init__(
            self,
            *,
            browser: str = "chrome",
            binary_location: Optional[str] = None,
            proxy_server: Optional[str] = None,
            extension_zip: Optional[str] = None,
            user_data_dir: Optional[str] = None,
            user_agent: Optional[str] = None,
            **sb_kwargs,
    ):
        """
        除显式列出的参数外，其余 **sb_kwargs 将原封不动透传给 SB。
        """
        self.sb = None
        self._sb_manager: Optional[SB] = None
        self._driver = None
        self._temp_dir = None

        # 处理扩展 zip：SB 要求传入绝对路径
        if extension_zip and not os.path.isabs(extension_zip):
            extension_zip = os.path.abspath(extension_zip)

        # 处理 user_data_dir：SB 需要绝对路径
        if user_data_dir and not os.path.isabs(user_data_dir):
            user_data_dir = os.path.abspath(user_data_dir)

        # 构造 SB 启动参数
        sb_options = {
            "browser": browser,
            "binary_location": binary_location,
            "proxy": proxy_server,
            "extension_zip": extension_zip,
            "user_data_dir": user_data_dir,
            "agent": user_agent,
            **sb_kwargs,
        }

        # 启动 SB
        self._sb_manager = SB(**sb_options)
        self.sb = self._sb_manager.__enter__()
        self._driver = self.sb.driver  # 暴露原生 Driver

    @property
    def driver(self):
        """返回 Selenium WebDriver 实例"""
        return self._driver

    def dispose(self):
        """
        手动关闭浏览器、WebDriver 并清理临时文件。
        可重复调用，不会抛异常。
        """
        if self._sb_manager is not None:
            try:
                self._sb_manager.__exit__(None, None, None)
            except Exception:
                pass
            finally:
                self._sb_manager = None
                self._driver = None

        # 清理 SB 可能遗留的临时目录
        if self._temp_dir and os.path.isdir(self._temp_dir):
            try:
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:
                pass
            self._temp_dir = None

    # 兼容 with 语法糖，但非必需
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()


# ---------------------------------------------------------------------- #
# DEMO（非上下文管理器）
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    # Windows下不能使用由管理员权限创建的console来进入ipython运行
    wrapper = SBOmniWrapper(
        binary_location="C:\Program Files\Google\Chrome\Application\chrome.exe",
        proxy="127.0.0.1:5082",
        # extension_zip="/tmp/my_ext.zip",
        user_data_dir=r"C:\Users\ckhoi\PycharmProjects\atelier-medusa\tmp\ud",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
        uc=True,
        # uc_subprocess=False
        # uc_cdp_events=True
    )

    # wrapper = SBOmniWrapper(
    #     binary_location="/usr/bin/google-chrome-stable",
    #     proxy="127.0.0.1:5082",
    #     # extension_zip="/tmp/my_ext.zip",
    #     user_data_dir=r"/tmp/ud",
    #     user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
    #     uc = True,
    #     headless = False,
    # )


    driver = wrapper.driver
    driver.get("https://ipinfo.io")
    time.sleep(5)
    wrapper.dispose()
