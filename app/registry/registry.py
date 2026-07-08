from typing import Dict, Any

class Registry:
    def __init__(self):
        self._items: Dict[str, Any] = {}

    def register(self, name, obj):
        if name in self._items:
            raise ValueError(f"{name} already registered.")
        self._items[name]=obj

    def unregister(self,name):
        self._items.pop(name,None)

    def get(self,name):
        return self._items.get(name)

    def exists(self,name):
        return name in self._items

    def clear(self):
        self._items.clear()

    def all(self):
        return self._items
