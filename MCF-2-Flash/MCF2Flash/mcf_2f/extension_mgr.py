from typing import Any, Dict, List, Optional
from stevedore import ExtensionManager, NamedExtensionManager


class ExtLoader:
    """
    轻量级 stevedore 扩展加载器
    --------------------------------
    1) 支持按 entry-point 名称空间加载所有扩展
    2) 支持按名字过滤/获取
    3) 支持直接调用扩展暴露的接口
    4) 支持运行时重载（reload）
    """

    def __init__(self,
                 namespace: str,
                 names: Optional[List[str]] = None,
                 invoke_on_load: bool = True,
                 invoke_args: tuple = (),
                 invoke_kwds: Optional[Dict[str, Any]] = None):
        """
        :param namespace:        setuptools entry-point 的命名空间
        :param names:            只加载指定的名字列表；None 表示全部
        :param invoke_on_load:   是否在加载时实例化扩展对象
        :param invoke_args:      实例化时传给扩展的 *args
        :param invoke_kwds:      实例化时传给扩展的 **kwargs
        """
        self.namespace = namespace
        self._names = names
        self._invoke_on_load = invoke_on_load
        self._invoke_args = invoke_args
        self._invoke_kwds = invoke_kwds or {}

        self._mgr = None
        self._reload()

    # ------------- 内部工具 -------------
    @staticmethod
    def _on_load_failure_callback(manager, entry_point, exception):
        # 直接抛出，让调用方立即感知
        raise exception

    def _reload(self):
        """重新扫描 entry-point 并创建 ExtensionManager"""
        kwargs = dict(
            invoke_on_load=self._invoke_on_load,
            invoke_args=self._invoke_args,
            invoke_kwds=self._invoke_kwds,
            on_load_failure_callback=self._on_load_failure_callback,
        )
        if self._names is None:
            self._mgr = ExtensionManager(self.namespace, **kwargs)
        else:
            self._mgr = NamedExtensionManager(
                self.namespace, names=self._names, **kwargs
            )

    # ------------- 对外 API -------------
    def extensions(self):
        """返回所有已加载的扩展对象列表"""
        return [ext.obj for ext in self._mgr.extensions]

    def map(self, method: str, *args, **kw):
        """
        对所有扩展调用同名方法，返回 {name: result} 字典
        例: loader.map('process', data)
        """
        return self._mgr.map(lambda ext: getattr(ext.obj, method)(*args, **kw))

    def call(self, name: str, method: str, *args, **kw):
        """对指定扩展调用方法"""
        ext = self._mgr[name]
        return getattr(ext.obj, method)(*args, **kw)

    def reload(self):
        """手动重载扩展（热插拔场景）"""
        self._reload()

    def __getitem__(self, name: str):
        """支持 loader['my_plugin'] 语法"""
        return self._mgr[name].obj

    def __iter__(self):
        return iter(self._mgr.names())
