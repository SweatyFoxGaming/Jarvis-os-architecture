from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(slots=True)
class ObservationEvent:
    trace_id: str
    source: str
    event: str
    payload: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)


def new_trace() -> str:
    return str(uuid4())
