class AuthManager:
    def __init__(self):
        self.access_token=None

    def set_token(self, token:str):
        self.access_token=token

    def get_token(self):
        return self.access_token
