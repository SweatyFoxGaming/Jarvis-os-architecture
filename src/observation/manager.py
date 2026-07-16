from .telemetry import Telemetry


class ObservationManager:

    def __init__(self):

        self.telemetry = Telemetry()

    def publish(self, event):

        self.telemetry.publish(event)

    def trace(self, trace):

        return self.telemetry.trace(trace)
