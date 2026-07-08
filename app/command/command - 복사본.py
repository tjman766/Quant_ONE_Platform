from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class Command:
    name: str
    payload: Any=None
