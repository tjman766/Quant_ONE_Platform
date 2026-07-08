from collections import defaultdict
from typing import DefaultDict, List
from .event import Event
from .subscriber import Subscriber
from .publisher import Publisher

class EventBus(Publisher):
    def __init__(self):
        self._subs: DefaultDict[str,List[Subscriber]] = defaultdict(list)

    def subscribe(self, event_name:str, subscriber:Subscriber)->None:
        if subscriber not in self._subs[event_name]:
            self._subs[event_name].append(subscriber)

    def unsubscribe(self,event_name:str, subscriber:Subscriber)->None:
        if subscriber in self._subs[event_name]:
            self._subs[event_name].remove(subscriber)

    def publish(self,event:Event)->None:
        for s in list(self._subs.get(event.name,[])):
            s.handle(event)
