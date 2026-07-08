from dataclasses import dataclass

@dataclass(slots=True)
class OAuthRequest:
    appkey: str
    appsecret: str
    grant_type: str = "client_credentials"
