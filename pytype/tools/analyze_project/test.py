import requests
import json as _json

class ClientException(Exception):
    pass

def check_error(json):
    """
    检测微信公众平台返回值中是否包含错误的返回码。
    如果返回码提示有错误，抛出一个 :class:`ClientException` 异常。否则返回 True 。
    """
    if "errcode" in json and json["errcode"] != 0:
        raise ClientException("{}: {}".format(json["errcode"], json["errmsg"]))
    return json

class Client(object):
    """
    微信 API 操作类
    通过这个类可以方便的通过微信 API 进行一系列操作，比如主动发送消息、创建自定义菜单等
    """
    def __init__(self, config):
        self.config = config
        self._token = None
        self.token_expires_at = None

    def request(self, method, url, **kwargs):
        if "params" not in kwargs:
            kwargs["params"] = {"access_token": self._token}
        if isinstance(kwargs.get("data", ""), dict):
            body = _json.dumps(kwargs["data"], ensure_ascii=False)
            body = body.encode('utf8')
            kwargs["data"] = body

        r = requests.request(method=method, url=url, **kwargs)
        r.raise_for_status()
        r.encoding = "utf-8"
        json = r.json()
        if check_error(json):
            return json


c = Client('config')
c.request(method="get", url='www.example.com', params={"grant_type": "client_credential"})
