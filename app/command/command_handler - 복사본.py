from abc import ABC, abstractmethod
from .command import Command

class CommandHandler(ABC):
    @abstractmethod
    def handle(self, command: Command):
        ...
