import redis


class SimpleRedis:
    """
    极简 Redis 客户端封装
    用法：
        r = SimpleRedis("127.0.0.1:6379/0")
        r.set("foo", "bar")
        print(r.get("foo"))   # -> bar
    """

    def __init__(self, url: str):
        # 直接让 redis-py 解析完整 URL
        self._cli = redis.Redis.from_url(
            url,
            decode_responses=True  # 仍保持返回 str
        )

    # 写数据
    def set(self, key, value, expire_time=None):
        """
        设置值

        :param key:
        :param value:
        :param expire_time: 过期时间（单位为秒）
        :return:
        """
        return self._cli.set(key, value, ex=expire_time)

    # 读数据
    def get(self, key):
        return self._cli.get(key)

    # 按需扩展
    def delete(self, *keys):
        return self._cli.delete(*keys)

    def exists(self, key):
        return bool(self._cli.exists(key))


if __name__ == '__main__':
    r = SimpleRedis("192.168.81.134:6379/1")
