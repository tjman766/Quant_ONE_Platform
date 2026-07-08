class RequestManager:
    def __init__(self, client):
        self.client=client
    def execute(self, method,path,**kwargs):
        return getattr(self.client,method.lower())(path,**kwargs)
