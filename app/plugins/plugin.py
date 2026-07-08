from abc import ABC, abstractmethod
from .metadata import PluginMetadata

class Plugin(ABC):
    metadata: PluginMetadata

    @abstractmethod
    def initialize(self)->None:
        ...
