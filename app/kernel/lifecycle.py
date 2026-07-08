from abc import ABC, abstractmethod

class Lifecycle(ABC):
    @abstractmethod
    def start(self): ...
    @abstractmethod
    def stop(self): ...
