from .settings import Settings

def validate(settings: Settings):
    if settings.active_profile not in ("MOCK","LIVE"):
        raise ValueError("Invalid KIWOOM_ACTIVE_PROFILE")
    return True
