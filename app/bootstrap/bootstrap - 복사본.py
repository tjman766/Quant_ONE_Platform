from app.container import Container
from app.events import EventBus

container=Container()

def bootstrap():
    container.register("event_bus", EventBus, singleton=True)
    return container
