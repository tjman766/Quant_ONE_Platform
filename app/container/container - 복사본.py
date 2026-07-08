from .provider import Provider

class Container:
    def __init__(self):
        self._providers={}
        self._instances={}

    def register(self,key,factory,singleton=True):
        self._providers[key]=Provider(factory,singleton)

    def resolve(self,key):
        provider=self._providers[key]
        if provider.singleton:
            if key not in self._instances:
                self._instances[key]=provider.factory()
            return self._instances[key]
        return provider.factory()

    def clear(self):
        self._providers.clear()
        self._instances.clear()
