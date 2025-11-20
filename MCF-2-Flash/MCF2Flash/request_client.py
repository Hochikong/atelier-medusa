import requests
import json
import uuid

class MCF2FlashClient:
    def __init__(self, base_url="http://localhost:8081"):
        self.base_url = base_url.rstrip('/')
        
    def send_single_task(self, url):
        """
        发送常规单个任务
        
        :param url: 要处理的URL
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/tasks/single/"
        payload = {
            "url": url
        }
        response = requests.post(endpoint, json=payload)
        return response.json()
        
    def send_special_task(self, url, driver, extra_content=None):
        """
        发送特殊任务一次性提交
        
        :param url: 要处理的URL
        :param driver: 驱动信息(namespace:DRIVER_NAME)
        :param extra_content: 额外内容(可选)
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/tasks/single/special"
        payload = {
            "url": url,
            "driver": driver
        }
        if extra_content is not None:
            payload["extra_content"] = extra_content
            
        response = requests.post(endpoint, json=payload)
        return response.json()
        
    def send_bulk_tasks(self, urls, download_child_dir=None):
        """
        发送批量任务
        
        :param urls: URL列表
        :param download_child_dir: 下载子目录(可选)
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/tasks/bulk/"
        params = {}
        if download_child_dir:
            params["download_child_dir"] = download_child_dir
            
        payload = {
            "urls": urls,
            "params": params
        }
        response = requests.post(endpoint, json=payload)
        return response.json()
        
    def init_browser(self):
        """
        初始化浏览器
        
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/init_browser"
        response = requests.get(endpoint)
        return response.json()
        
    def dispose_browser(self):
        """
        销毁浏览器
        
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/dispose_browser"
        response = requests.get(endpoint)
        return response.json()
        
    def get_task_by_uid(self, uid):
        """
        根据UID获取任务
        
        :param uid: 任务UID
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/tasks/{uid}"
        response = requests.get(endpoint)
        return response.json()
        
    def get_tasks_by_status(self, status_code):
        """
        根据状态码获取任务
        
        :param status_code: 状态码
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/tasks/status/"
        params = {"code": status_code}
        response = requests.get(endpoint, params=params)
        return response.json()
        
    def run_not_done_tasks(self):
        """
        运行未完成的任务
        
        :return: 服务器响应
        """
        endpoint = f"{self.base_url}/mcf/v2/tasks/run_not_done"
        response = requests.post(endpoint)
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = MCF2FlashClient("http://192.168.31.204:8081")
    
    # 示例1: 发送特殊任务
    result = client.send_special_task(
        url="https://example.com", 
        driver="namespace:DRIVER_NAME",
        extra_content='{"key": "value"}'
    )
    print("发送特殊任务:", result)
    
    # 示例2: 发送常规单个任务
    result = client.send_single_task("https://example.com")
    print("发送常规单个任务:", result)
    
    # 示例3: 发送批量任务
    result = client.send_bulk_tasks([
        "https://example.com/page1",
        "https://example.com/page2"
    ], download_child_dir="downloads")
    print("发送批量任务:", result)
    
    # 示例4: 初始化浏览器
    result = client.init_browser()
    print("初始化浏览器:", result)