import time

class IntervalTrigger:
    def __init__(self, interval:float):
        self.interval=interval
        self._last=0.0
    def ready(self)->bool:
        now=time.time()
        if now-self._last>=self.interval:
            self._last=now
            return True
        return False
