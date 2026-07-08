from app.integration import ApiClient

class KiwoomClient(ApiClient):
    def get(self, path:str, **kwargs):
        raise NotImplementedError("Implement Kiwoom REST GET")

    def post(self, path:str, **kwargs):
        raise NotImplementedError("Implement Kiwoom REST POST")
