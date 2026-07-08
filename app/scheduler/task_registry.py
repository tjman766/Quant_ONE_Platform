class TaskRegistry:
    def __init__(self):
        self._tasks={}
    def register(self,task):
        self._tasks[task.name]=task
    def all(self):
        return list(self._tasks.values())
