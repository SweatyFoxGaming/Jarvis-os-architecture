import pytest
from src.core.event_bus import EventBus
from src.core.models import Event

def test_event_bus_pub_sub():
    bus = EventBus()
    received = []

    def callback(event):
        received.append(event)

    bus.subscribe("test_event", callback)
    bus.publish(Event(event_type="test_event", source="test", payload={"msg": "hello"}))

    assert len(received) == 1
    assert received[0].payload["msg"] == "hello"

def test_generic_subscriber():
    bus = EventBus()
    received = []

    bus.subscribe("*", lambda e: received.append(e))
    bus.publish(Event(event_type="any", source="test"))

    assert len(received) == 1
