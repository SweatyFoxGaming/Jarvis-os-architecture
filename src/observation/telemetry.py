from collections import defaultdict

class Telemetry:

    def __init__(self):

        self.events = defaultdict(list)

    def publish(self, event):

        self.events[event.trace_id].append(event)

    def trace(self, trace_id):

        return self.events.get(trace_id, [])
