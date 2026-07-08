import os
from .settings import Settings

def load_settings():
    s=Settings()
    s.active_profile=os.getenv("KIWOOM_ACTIVE_PROFILE", s.active_profile)
    return s
