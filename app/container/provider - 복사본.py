from dataclasses import dataclass
from typing import Callable

@dataclass(slots=True)
class Provider:
    factory: Callable
    singleton: bool = True
