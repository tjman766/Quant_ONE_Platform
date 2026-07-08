import requests

class SessionManager:
    def __init__(self):
        self._session=requests.Session()
        self._session.headers.update({"Connection":"keep-alive"})

    @property
    def session(self):
        return self._session
