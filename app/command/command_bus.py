from .command import Command
from .command_registry import CommandRegistry

class CommandBus:
    def __init__(self):
        self.registry=CommandRegistry()

    def register(self, name, handler):
        self.registry.register(name, handler)

    def dispatch(self, command: Command):
        handler=self.registry.get(command.name)
        if handler is None:
            raise KeyError(f"No handler registered for '{command.name}'")
        return handler.handle(command)
