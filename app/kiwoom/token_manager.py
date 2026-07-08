from .oauth_service import OAuthService
from .oauth_request import OAuthRequest

class TokenManager:
    def __init__(self, oauth_service: OAuthService):
        self.oauth_service = oauth_service
        self._token = None

    def issue(self, appkey:str, appsecret:str):
        req = OAuthRequest(appkey=appkey, appsecret=appsecret)
        self._token = self.oauth_service.request_token(req)
        return self._token

    @property
    def token(self):
        return self._token
