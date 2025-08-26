import json
import yaml

def yaml_loader(path: str, encoding: str = 'utf-8') -> dict:
    """用于减少yaml配置文件读取的重复代码

    :param path: 文件的路径
    :param encoding: 编码
    :return: 当加载成功，返回有元素的dict，否则返回空dict
    """
    try:
        with open(path, 'r', encoding=encoding) as f:
            return yaml.load(f, yaml.FullLoader)
    except Exception as e:
        print(e)
        return {}


def yaml_writer(path: str, content: dict, encoding: str = 'utf-8') -> bool:
    """用于减少yaml配置文件输出的重复代码

    :param path: 文件输出路径
    :param content: 要写入文件的字典
    :param encoding: 编码，默认为utf-8
    :return: 布尔值
    """
    try:
        content = yaml.dump(content)
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(e)
        return False


def json_loader(path: str, encoding: str = 'utf-8') -> dict:
    """用于减少json文件读取的重复代码

    :param path:
    :param encoding:
    :return: 当加载成功，返回有元素的dict，否则返回空dict
    """
    try:
        with open(path, 'r', encoding=encoding) as f:
            return json.load(f)
    except Exception as e:
        print(e)
        return {}


def json_writer(path: str, content: dict, encoding: str = 'utf-8') -> bool:
    """确保支持导出非ascii字符的json文档

    :param path:
    :param content:
    :param encoding:
    :return:
    """
    try:
        with open(path, 'w', encoding=encoding) as f:
            json.dump(content, f, indent=4, ensure_ascii=False)
            return True
    except Exception as e:
        print(e)
        return False