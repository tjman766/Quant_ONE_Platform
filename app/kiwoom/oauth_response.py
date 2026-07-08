from dataclasses import dataclass

@dataclass(slots=True)
class OAuthResponse:
    access_token: str
    token_type: str
    expires_dt: str
