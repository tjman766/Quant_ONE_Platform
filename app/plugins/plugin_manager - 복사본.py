from .loader import PluginLoader

class PluginManager:
    def __init__(self):
        self.loader=PluginLoader()
        self.plugins={}

    def register(self, plugin_cls):
        plugin=self.loader.load(plugin_cls)
        plugin.initialize()
        self.plugins[plugin.metadata.name]=plugin

    def get(self,name):
        return self.plugins.get(name)
