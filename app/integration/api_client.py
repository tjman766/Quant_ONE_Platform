import requests
from .response_parser import ResponseParser

class ApiClient:
    def __init__(self, base_url:str):
        self.base_url=base_url.rstrip("/")
        self.session=requests.Session()
        self.parser=ResponseParser()

    def request(self, method:str, path:str, **kwargs):
        r=self.session.request(method, self.base_url+path, timeout=10, **kwargs)
        r.raise_for_status()
        return self.parser.parse(r.json())

    def get(self,path:str,**kwargs):
        return self.request("GET",path,**kwargs)

    def post(self,path:str,**kwargs):
        return self.request("POST",path,**kwargs)
