"""
Event Bus implementation for Phoenix OS.

Provides decoupled communication between components via publish/subscribe.
Now with logging, unsubscribe support, and optional audit logging to secure memory.
"""

import collections
import logging
from typing import Any, Callable, Dict, List, Optional

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.core.interfaces import IEventBus
from src.core.models import Event

# Logger
logger = logging.getLogger(__name__)


class EventBus(IEventBus):
    """
    In‑memory event bus with wildcard support.
    Allows components to publish and subscribe to events.
    """

    def __init__(self):
        """
        Initialize the event bus with an empty subscriber dictionary.
        """
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = collections.defaultdict(list)
        self._secure_memory: Optional[SecureMemoryStore] = None
        self._secure_runner: Optional[SecureCommandRunner] = None
        logger.info("[EventBus] Initialized.")

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info("[EventBus] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        self._secure_runner = secure_runner
        logger.info("[EventBus] SecureCommandRunner attached.")

    # ---------- Event Bus Interface ----------
    def publish(self, event: Event) -> None:
        """
        Publish an event to all registered subscribers.

        Args:
            event: The Event instance to publish.
        """
        logger.debug(f"[EventBus] Publishing: {event.event_type} from {event.source}")

        # Audit log (if secure memory is available)
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"EVENT: {event.event_type} from {event.source}",
                    metadata={
                        "type": "event_bus_audit",
                        "event_type": event.event_type,
                        "source": event.source,
                        "importance": event.importance,
                    },
                )
            except Exception as e:
                logger.warning(f"[EventBus] Failed to audit log event: {e}")

        # Notify specific event type subscribers
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"[EventBus] Error in callback for {event.event_type}: {e}",
                    exc_info=True,
                )

        # Notify wildcard subscribers
        for callback in self._subscribers.get("*", []):
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"[EventBus] Error in wildcard callback for {event.event_type}: {e}",
                    exc_info=True,
                )

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """
        Register a callback for a given event type.

        Args:
            event_type: The event type string (or "*" for wildcard).
            callback: Callable that accepts an Event parameter.
        """
        if not callable(callback):
            raise ValueError("Callback must be callable.")

        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        # Prevent duplicate registration (optional)
        if callback in self._subscribers[event_type]:
            logger.warning(f"[EventBus] Callback already registered for event '{event_type}'. Skipping duplicate.")
            return

        self._subscribers[event_type].append(callback)
        logger.debug(f"[EventBus] Subscribed to '{event_type}' (total: {len(self._subscribers[event_type])})")

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """
        Remove a previously registered callback for an event type.

        Args:
            event_type: The event type string.
            callback: The callback that was previously registered.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"[EventBus] Unsubscribed from '{event_type}'")
                # Clean up empty lists to keep the dict tidy
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
            except ValueError:
                logger.warning(f"[EventBus] Callback not found for event '{event_type}'")
        else:
            logger.warning(f"[EventBus] No subscribers for event '{event_type}'")

    def clear_subscribers(self) -> None:
        """Remove all subscribers (useful for testing or shutdown)."""
        self._subscribers.clear()
        logger.info("[EventBus] All subscribers cleared.")

    # ---------- Utility Methods ----------
    def list_subscribers(self) -> Dict[str, int]:
        """
        Return a dictionary of event types and the number of subscribers.

        Returns:
            Dict mapping event_type -> subscriber count.
        """
        return {event_type: len(callbacks) for event_type, callbacks in self._subscribers.items()}

    # ---------- Shutdown ----------
    def shutdown(self) -> None:
        """Clean up resources and clear subscribers."""
        logger.info("[EventBus] Shutting down.")
        self.clear_subscribers()

        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[EventBus] Error closing secure memory: {e}")
        self._secure_memory = None
        self._secure_runner = None
