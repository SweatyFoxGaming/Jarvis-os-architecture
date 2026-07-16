"""
Interaction Manager – The single entry point for all interactions.
Governed by INTERACTION_MODEL.md
"""

import logging
from typing import Optional, Generator, List, Dict, Any
from uuid import UUID

from src.interaction.models import Interaction, InteractionResponse, InteractionSource, InteractionKind, Notification, NotificationType
from src.interaction.session_manager import SessionManager
from src.interaction.conversation_engine import ConversationEngine
from src.interaction.notification_manager import NotificationManager

logger = logging.getLogger(__name__)


class InteractionManager:
    """
    The entry point for all user interactions.
    Validates input, routes to appropriate engine, and returns responses.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        conversation_engine: ConversationEngine,
        notification_manager: NotificationManager,
    ):
        self.session_manager = session_manager
        self.conversation_engine = conversation_engine
        self.notification_manager = notification_manager
        logger.info("[InteractionManager] Initialized.")

    def handle(self, interaction: Interaction) -> InteractionResponse:
        """
        Process an interaction synchronously.
        """
        if not interaction.session_id:
            raise ValueError("session_id is required")
        if not interaction.content:
            raise ValueError("interaction content is required")

        if interaction.kind in [InteractionKind.TEXT, InteractionKind.VOICE, InteractionKind.COMMAND]:
            return self.conversation_engine.process_interaction(interaction)
        else:
            return InteractionResponse(
                text=f"Received {interaction.kind} interaction. Processing not yet implemented.",
                metadata={"error": "unsupported interaction kind"}
            )

    def handle_stream(self, interaction: Interaction) -> Generator[str, None, None]:
        """
        Process an interaction and stream the response.
        """
        if interaction.kind in [InteractionKind.TEXT, InteractionKind.VOICE, InteractionKind.COMMAND]:
            yield from self.conversation_engine.process_interaction_stream(interaction)
        else:
            yield "Unsupported interaction kind for streaming."

    # ---------- Notification Convenience Methods ----------
    def notify(self, session_id: UUID, notification_type: NotificationType, title: str, body: str, actions: List[Dict[str, Any]] = None, priority: int = 1) -> None:
        """Publish a notification to a session."""
        self.notification_manager.publish_to_session(session_id, notification_type, title, body, actions, priority)

    def get_notifications(self, session_id: UUID, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        """Get notifications for a session."""
        if unread_only:
            return self.notification_manager.get_unread(session_id)
        return self.notification_manager.get_all(session_id, limit)

    def mark_read(self, notification_id: UUID) -> bool:
        return self.notification_manager.mark_read(notification_id)

    def mark_all_read(self, session_id: UUID) -> int:
        return self.notification_manager.mark_all_read(session_id)

    def get_stream_queue(self, session_id: UUID):
        """Get the SSE queue for a session."""
        return self.notification_manager.get_queue(session_id)

    def remove_stream_queue(self, session_id: UUID) -> None:
        """Remove the SSE queue for a session."""
        self.notification_manager.remove_queue(session_id)
