from dataclasses import dataclass
from datetime import datetime

@dataclass(slots=True)
class OAuthToken:
    access_token: str = ""
    token_type: str = "Bearer"
    expires_at: datetime | None = None
