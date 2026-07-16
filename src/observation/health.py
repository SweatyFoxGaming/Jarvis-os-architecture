from enum import Enum


class HealthState(str, Enum):

    HEALTHY = "healthy"

    BUSY = "busy"

    DEGRADED = "degraded"

    OFFLINE = "offline"

    DISABLED = "disabled"
