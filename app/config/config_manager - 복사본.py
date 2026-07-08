from .env_loader import load_settings
from .validator import validate

class ConfigManager:
    def __init__(self):
        self.settings=load_settings()
        validate(self.settings)

    def get_settings(self):
        return self.settings
