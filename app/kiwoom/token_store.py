class TokenStore:
    def __init__(self):
        self._token = None

    def save(self, token):
        self._token = token

    def load(self):
        return self._token

    def clear(self):
        self._token = None
