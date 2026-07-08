from .endpoints import OAUTH_TOKEN
from .oauth_request import OAuthRequest

class OAuthService:
    def __init__(self, client):
        self.client = client

    def request_token(self, request: OAuthRequest):
        # TODO: Replace payload/response mapping with the official Kiwoom REST API spec.
        payload = {
            "grant_type": request.grant_type,
            "appkey": request.appkey,
            "appsecret": request.appsecret,
        }
        return self.client.post(OAUTH_TOKEN, json=payload)
