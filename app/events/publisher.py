from abc import ABC, abstractmethod
from .event import Event

class Publisher(ABC):
    @abstractmethod
    def publish(self, event: Event) -> None:
        ...
