from abc import ABCMeta, abstractmethod
from seleniumbase import SB
from typing import Optional


class MockSBOmniWrapper:
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

        # 启动 SB
        self._sb_manager = SB()
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
        pass

    # 兼容 with 语法糖，但非必需
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()


class AbstractExtensionMCFV2(metaclass=ABCMeta):
    """
    驱动的抽象基类

    """

    @abstractmethod
    def prepare(self, instance: MockSBOmniWrapper, config: dict, **kwargs) -> tuple:
        """
        初始化阶段

        :param instance: 浏览器实例对象
        :param config: 注入的配置信息
        :param kwargs:

        :return: 返回长度为2的元组，当执行成功时，返回的元组中，第一个元素表示操作成功与否，第二个元素表示相关的信息，
                 例如：(True, "prepare阶段成功"), (False, "prepare阶段失败，原因为xxxx")
        """
        pass

    @abstractmethod
    def handle(self) -> tuple:
        """
        实际的执行阶段

        :return: 返回长度为2的元组，当执行成功时，返回的元组中，第一个元素表示操作成功与否，第二个元素表示相关的信息，
                例如：(True, "prepare阶段成功"), (False, "prepare阶段失败，原因为xxxx")
        """
        pass

    @abstractmethod
    def parse_extension_config(self, config: dict):
        """
        解析插件的配置信息，用于校验插件支持的参数是否齐全，顺便起到解析的作用，会调用get_name从配置中读取对应的部分

        :param config: 主配置文件中的Extensions片段，参考下面的YAML格式
                       Extensions:
                         namespace: mcf_v2
                         ByExtensions:

                           plugin_1:
                             author: xxx
                             target_list:

                       解析后应该是：
                       {'Extensions':
                         {'namespace': 'mcf_v2', 'ByExtensions': {
                            'plugin_1': {'author': xxx, 'target_list': []}
                         }
                       }
        :return:
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        插件的唯一名称

        :return:
        """
        pass

    @abstractmethod
    def get_plugin_return(self) -> dict:
        """
        获取插件的相关信息统计和结果返回等信息，具体内容由插件自身实现

        :param on:
        :return:
        """
        pass
