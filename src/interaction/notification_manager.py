"""
Notification Manager – Proactive communication with SSE support.
Governed by INTERACTION_MODEL.md
"""

import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any
from uuid import UUID
from datetime import datetime
from collections import defaultdict

from src.interaction.models import Notification, NotificationType
from src.core.interfaces import IEventBus
from src.core.models import Event

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages subscriptions and delivery of notifications.
    Supports SSE streaming via per‑session queues.
    """

    def __init__(self, event_bus: Optional[IEventBus] = None):
        self._subscriptions: Dict[UUID, List[Callable]] = {}
        self._queues: Dict[UUID, asyncio.Queue] = {}
        self._notifications: List[Notification] = []
        self._event_bus = event_bus

        if event_bus:
            self._subscribe_to_event_bus(event_bus)

        logger.info("[NotificationManager] Initialized.")

    # ---------- Event Bus Integration ----------
    def _subscribe_to_event_bus(self, event_bus: IEventBus) -> None:
        """Subscribe to internal events and convert them to Notifications."""
        event_bus.subscribe("TaskCompleted", self._on_task_completed)
        event_bus.subscribe("TaskFailed", self._on_task_failed)
        event_bus.subscribe("OperationalEscalation", self._on_operational_escalation)
        event_bus.subscribe("DepartmentAssigned", self._on_department_assigned)
        logger.info("[NotificationManager] Subscribed to EventBus events.")

    def _on_task_completed(self, event: Event) -> None:
        """Convert TaskCompleted to a notification."""
        task_id = event.payload.get("task_id")
        if not task_id:
            return
        # Try to get session_id from the event
        session_id = event.payload.get("session_id") or event.payload.get("goal_uuid")
        if not session_id:
            # If we can't find a session, we can't deliver the notification
            logger.debug(f"[NotificationManager] No session_id for TaskCompleted {task_id}")
            return

        # Convert to a Notification
        notification = Notification(
            session_id=session_id if isinstance(session_id, UUID) else UUID(session_id),
            type=NotificationType.TASK_COMPLETED,
            title="Task Completed",
            body=f"Task {task_id} has been completed successfully.",
            actions=[{"label": "View Details", "action": "view_task", "task_id": task_id}],
            priority=1,
        )
        self.publish(notification)

    def _on_task_failed(self, event: Event) -> None:
        """Convert TaskFailed to a notification."""
        task_id = event.payload.get("task_id")
        error = event.payload.get("error", "Unknown error")
        session_id = event.payload.get("session_id")
        if not session_id:
            return
        notification = Notification(
            session_id=session_id if isinstance(session_id, UUID) else UUID(session_id),
            type=NotificationType.TASK_FAILED,
            title="Task Failed",
            body=f"Task {task_id} failed: {error}",
            actions=[{"label": "Retry", "action": "retry_task", "task_id": task_id}],
            priority=2,
        )
        self.publish(notification)

    def _on_operational_escalation(self, event: Event) -> None:
        """Convert OperationalEscalation to a warning notification."""
        reason = event.payload.get("reason", "Unknown issue")
        session_id = event.payload.get("session_id")
        if not session_id:
            return
        notification = Notification(
            session_id=session_id if isinstance(session_id, UUID) else UUID(session_id),
            type=NotificationType.WARNING,
            title="Warning",
            body=f"Operational issue: {reason}",
            priority=2,
        )
        self.publish(notification)

    def _on_department_assigned(self, event: Event) -> None:
        """Optionally notify about task assignment (low priority)."""
        task_id = event.payload.get("task_id")
        department = event.payload.get("department")
        session_id = event.payload.get("session_id")
        if not session_id:
            return
        notification = Notification(
            session_id=session_id if isinstance(session_id, UUID) else UUID(session_id),
            type=NotificationType.INSIGHT,
            title="Task Assigned",
            body=f"Task {task_id} assigned to {department}",
            priority=0,  # low priority
        )
        self.publish(notification)

    # ---------- Subscription Management ----------
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

    # ---------- SSE Queue Management ----------
    def get_queue(self, session_id: UUID) -> asyncio.Queue:
        """Get or create a queue for SSE streaming for a session."""
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
        return self._queues[session_id]

    def remove_queue(self, session_id: UUID) -> None:
        """Remove a queue when the client disconnects."""
        if session_id in self._queues:
            del self._queues[session_id]

    # ---------- Publishing ----------
    def publish(self, notification: Notification) -> None:
        """Send a notification to all subscribers and queues of the session."""
        self._notifications.append(notification)
        session_id = notification.session_id

        # Publish to callbacks
        if session_id in self._subscriptions:
            for callback in self._subscriptions[session_id]:
                try:
                    callback(notification)
                except Exception as e:
                    logger.error(f"[NotificationManager] Callback error: {e}")

        # Publish to queue for SSE
        if session_id in self._queues:
            try:
                self._queues[session_id].put_nowait(notification)
            except asyncio.QueueFull:
                logger.warning(f"[NotificationManager] Queue full for session {session_id}")
            except Exception as e:
                logger.error(f"[NotificationManager] Queue error: {e}")
        else:
            logger.debug(f"[NotificationManager] No queue for session {session_id}")

    def publish_to_session(self, session_id: UUID, notification_type: NotificationType, title: str, body: str, actions: List[Dict[str, Any]] = None, priority: int = 1) -> None:
        """Convenience method to publish a notification to a specific session."""
        notification = Notification(
            session_id=session_id,
            type=notification_type,
            title=title,
            body=body,
            actions=actions or [],
            priority=priority,
        )
        self.publish(notification)

    # ---------- Retrieval ----------
    def get_unread(self, session_id: UUID) -> List[Notification]:
        """Return unread notifications for a session."""
        return [n for n in self._notifications if n.session_id == session_id and not n.read]

    def mark_read(self, notification_id: UUID) -> bool:
        for n in self._notifications:
            if n.id == notification_id:
                n.read = True
                return True
        return False

    def mark_all_read(self, session_id: UUID) -> int:
        """Mark all notifications for a session as read."""
        count = 0
        for n in self._notifications:
            if n.session_id == session_id and not n.read:
                n.read = True
                count += 1
        return count

    def get_all(self, session_id: UUID, limit: int = 50) -> List[Notification]:
        """Return all notifications for a session (most recent first)."""
        filtered = [n for n in self._notifications if n.session_id == session_id]
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered[:limit]
