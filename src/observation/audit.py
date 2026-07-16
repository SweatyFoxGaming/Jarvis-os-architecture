from dataclasses import dataclass
from datetime import datetime


@dataclass

class AuditRecord:

    actor: str

    action: str

    details: dict

    timestamp: datetime = datetime.utcnow()
