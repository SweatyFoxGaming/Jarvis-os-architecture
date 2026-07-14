"""
Interaction Manager – The single entry point for all interactions.
Governed by INTERACTION_MODEL.md
"""

import logging
from typing import Optional, Generator
from uuid import UUID

from src.interaction.models import Interaction, InteractionResponse, InteractionSource, InteractionKind
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
        # Basic validation
        if not interaction.session_id:
            raise ValueError("session_id is required")
        if not interaction.content:
            raise ValueError("interaction content is required")

        # Route based on kind/source
        # For simplicity, all interactions go to conversation engine for now.
        # Future: route to system events, capability events, etc.
        if interaction.kind in [InteractionKind.TEXT, InteractionKind.VOICE, InteractionKind.COMMAND]:
            return self.conversation_engine.process_interaction(interaction)
        else:
            # Handle file, image, etc. later
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

    def notify(self, notification):
        """Send a notification via the notification manager."""
        self.notification_manager.publish(notification)
