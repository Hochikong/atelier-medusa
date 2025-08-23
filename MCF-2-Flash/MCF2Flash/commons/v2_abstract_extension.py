from abc import ABCMeta, abstractmethod
from seleniumbase import SB, Driver
from typing import Any, Optional


class AbstractExtensionMCFV2(metaclass=ABCMeta):
    """
    驱动的抽象基类

    """

    @abstractmethod
    def prepare(self, instance: Optional[SB, Driver], config: dict, **kwargs) -> tuple:
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
