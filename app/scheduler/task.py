from dataclasses import dataclass
from typing import Callable

@dataclass(slots=True)
class Task:
    name:str
    action:Callable
    interval:float=1.0
