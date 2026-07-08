class CommandRegistry:
    def __init__(self):
        self._handlers={}
    def register(self, name, handler):
        self._handlers[name]=handler
    def get(self, name):
        return self._handlers.get(name)
