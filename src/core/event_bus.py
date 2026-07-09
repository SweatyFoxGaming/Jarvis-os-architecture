import collections
from typing import Any, Callable, Dict, List
from src.core.interfaces import IEventBus
from src.core.models import Event

class EventBus(IEventBus):
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = collections.defaultdict(list)

    def publish(self, event: Event) -> None:
        print(f"[EventBus] Publishing: {event.event_type} from {event.source}")
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                print(f"[EventBus] Error in callback for {event.event_type}: {e}")

        # Generic subscribers
        for callback in self._subscribers.get("*", []):
            callback(event)

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        self._subscribers[event_type].append(callback)
