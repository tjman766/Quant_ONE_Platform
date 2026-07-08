from .application import Application
from .state import AppState
from app.bootstrap import bootstrap

class Kernel:
    def __init__(self):
        self.container=bootstrap()
        self.app=Application()

    def start(self):
        self.app.state=AppState.STARTING
        self.app.state=AppState.RUNNING

    def stop(self):
        self.app.state=AppState.STOPPING
        self.app.state=AppState.STOPPED
