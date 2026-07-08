from .logger import get_logger

class LogManager:
    def __init__(self):
        self._cache = {}

    def logger(self, name: str):
        if name not in self._cache:
            self._cache[name] = get_logger(name)
        return self._cache[name]
