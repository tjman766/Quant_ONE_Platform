from .state import AppState

class Application:
    def __init__(self):
        self.state=AppState.CREATED
