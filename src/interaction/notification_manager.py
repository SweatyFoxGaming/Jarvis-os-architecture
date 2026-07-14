"""
Notification Manager – Proactive communication.
Governed by INTERACTION_MODEL.md
"""

import logging
from typing import Dict, List, Optional, Callable
from uuid import UUID

from src.interaction.models import Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages subscriptions and delivery of notifications.
    In-memory pub/sub for now.
    """

    def __init__(self):
        self._subscriptions: Dict[UUID, List[Callable]] = {}
        self._notifications: List[Notification] = []
        logger.info("[NotificationManager] Initialized.")

    def subscribe(self, session_id: UUID, callback: Callable) -> None:
        """Register a callback for a session."""
        if session_id not in self._subscriptions:
            self._subscriptions[session_id] = []
        self._subscriptions[session_id].append(callback)
        logger.debug(f"[NotificationManager] Subscribed session {session_id}")

    def unsubscribe(self, session_id: UUID, callback: Callable) -> None:
        """Remove a callback for a session."""
        if session_id in self._subscriptions:
            self._subscriptions[session_id] = [cb for cb in self._subscriptions[session_id] if cb != callback]

    def publish(self, notification: Notification) -> None:
        """Send a notification to all subscribers of the session."""
        self._notifications.append(notification)
        session_id = notification.session_id
        if session_id in self._subscriptions:
            for callback in self._subscriptions[session_id]:
                try:
                    callback(notification)
                except Exception as e:
                    logger.error(f"[NotificationManager] Callback error: {e}")
        else:
            logger.debug(f"[NotificationManager] No subscribers for session {session_id}")

    def get_unread(self, session_id: UUID) -> List[Notification]:
        """Return unread notifications for a session."""
        return [n for n in self._notifications if n.session_id == session_id and not n.read]

    def mark_read(self, notification_id: UUID) -> bool:
        for n in self._notifications:
            if n.id == notification_id:
                n.read = True
                return True
        return False
