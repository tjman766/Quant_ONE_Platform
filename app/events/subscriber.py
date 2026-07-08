from abc import ABC, abstractmethod
from .event import Event

class Subscriber(ABC):
    @abstractmethod
    def handle(self, event: Event) -> None:
        ...
