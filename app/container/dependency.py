from dataclasses import dataclass

@dataclass(slots=True)
class Dependency:
    key: str
    singleton: bool = True
