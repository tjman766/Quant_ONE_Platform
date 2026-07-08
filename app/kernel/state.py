from enum import Enum

class AppState(Enum):
    CREATED="created"
    STARTING="starting"
    RUNNING="running"
    STOPPING="stopping"
    STOPPED="stopped"
