from dataclasses import dataclass

@dataclass(slots=True)
class PluginMetadata:
    name:str
    version:str="0.1.0"
    author:str=""
