"""
Environment Platform – Local Calendar provider.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.environment.providers.base import EnvironmentProvider
from src.environment.models import ProviderHealth, ProviderMetadata, Domain, EnvironmentProviderCapability

logger = logging.getLogger(__name__)


class LocalCalendarProvider(EnvironmentProvider):
    """
    Local calendar provider using a JSON file.
    """

    def __init__(self, secure_memory=None, calendar_file: Optional[str] = None):
        self.secure_memory = secure_memory
        self.calendar_file = calendar_file or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "calendar.json")
        self._health = ProviderHealth.LOADING
        self._initialized = False

    def _load_calendar(self) -> List[Dict]:
        if not os.path.exists(self.calendar_file):
            return []
        try:
            with open(self.calendar_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def _save_calendar(self, events: List[Dict]) -> None:
        os.makedirs(os.path.dirname(self.calendar_file), exist_ok=True)
        with open(self.calendar_file, 'w') as f:
            json.dump(events, f, indent=2)

    def initialize(self) -> None:
        self._health = ProviderHealth.AVAILABLE
        self._initialized = True
        logger.info("[LocalCalendarProvider] Initialized.")

    def shutdown(self) -> None:
        self._health = ProviderHealth.OFFLINE
        self._initialized = False
        logger.info("[LocalCalendarProvider] Shut down.")

    def health(self) -> ProviderHealth:
        return self._health

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="local_calendar",
            domain=Domain.CALENDAR,
            version="1.0.0",
            author="Jarvis Core Team",
            description="Local calendar storage using JSON file.",
            capabilities=[
                EnvironmentProviderCapability(
                    name="list_events",
                    description="List all calendar events",
                    parameters={},
                    returns={"events": {"type": "array"}}
                ),
                EnvironmentProviderCapability(
                    name="add_event",
                    description="Add a new event",
                    parameters={"title": {"type": "string"}, "date": {"type": "string"}, "description": {"type": "string"}},
                    returns={"event": {"type": "object"}, "message": {"type": "string"}}
                ),
                EnvironmentProviderCapability(
                    name="remove_event",
                    description="Remove an event by ID",
                    parameters={"event_id": {"type": "integer"}},
                    returns={"message": {"type": "string"}}
                ),
            ]
        )

    def capabilities(self) -> List[str]:
        return ["list_events", "add_event", "remove_event"]

    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Provider not initialized"}

        try:
            if capability == "list_events":
                events = self._load_calendar()
                return {"events": events}

            elif capability == "add_event":
                title = params.get('title')
                if not title:
                    return {"error": "Missing 'title'"}
                date = params.get('date', datetime.now().isoformat())
                description = params.get('description', "")
                events = self._load_calendar()
                event_id = max([e.get('id', 0) for e in events]) + 1 if events else 1
                event = {"id": event_id, "title": title, "date": date, "description": description}
                events.append(event)
                self._save_calendar(events)
                return {"event": event, "message": "Event added"}

            elif capability == "remove_event":
                event_id = params.get('event_id') or params.get('id')
                if event_id is None:
                    return {"error": "Missing 'event_id'"}
                events = self._load_calendar()
                new_events = [e for e in events if e.get('id') != event_id]
                if len(new_events) == len(events):
                    return {"error": "Event not found"}
                self._save_calendar(new_events)
                return {"message": "Event removed"}

            else:
                return {"error": f"Unknown capability: {capability}"}

        except Exception as e:
            logger.error(f"[LocalCalendarProvider] Error executing {capability}: {e}", exc_info=True)
            return {"error": str(e)}
