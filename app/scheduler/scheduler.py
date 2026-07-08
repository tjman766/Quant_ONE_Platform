from .task_registry import TaskRegistry
from .trigger import IntervalTrigger

class Scheduler:
    def __init__(self):
        self.registry=TaskRegistry()
        self._triggers={}
    def add_task(self,task):
        self.registry.register(task)
        self._triggers[task.name]=IntervalTrigger(task.interval)
    def tick(self):
        for task in self.registry.all():
            if self._triggers[task.name].ready():
                task.action()
