"""
Conversation Engine – Manages dialogue, streaming, and delegation.
Governed by INTERACTION_MODEL.md
"""

import logging
import json
from typing import Dict, Any, Optional, Generator, List
from uuid import UUID

from src.interaction.models import Interaction, InteractionResponse, Message, MessageRole, Session, Tone
from src.interaction.session_manager import SessionManager
from src.interaction.personality_engine import PersonalityEngine
from src.executive.mind import ExecutiveMind

logger = logging.getLogger(__name__)


class ConversationEngine:
    """
    Manages conversations and orchestrates the interaction flow:
    1. Receives Interaction
    2. Retrieves Session
    3. Builds prompt via PersonalityEngine
    4. Delegates to ExecutiveMind
    5. Constructs InteractionResponse
    """

    def __init__(self, session_manager: SessionManager, personality_engine: PersonalityEngine, executive: ExecutiveMind):
        self.session_manager = session_manager
        self.personality_engine = personality_engine
        self.executive = executive
        logger.info("[ConversationEngine] Initialized.")

    def process_interaction(self, interaction: Interaction) -> InteractionResponse:
        """
        Process a single interaction synchronously.
        Returns an InteractionResponse.
        """
        session = self.session_manager.get_or_create(interaction.session_id, interaction.metadata.get("user_id", "default"))
        tone = session.tone

        # Update session state
        self.session_manager.update_state(session.session_id, "thinking")

        # Build system prompt
        system_prompt = self.personality_engine.build_system_prompt(tone)

        # If interaction is text, pass to ExecutiveMind with custom prompt
        if interaction.kind == "text":
            user_text = interaction.content
            # Optionally include the tone instruction in the prompt
            # We'll pass it as an extra system instruction
            # We need to modify ExecutiveMind to accept system_prompt parameter; we'll adapt later.
            # For now, we'll assume ExecutiveMind's process_request can accept an optional override.
            response_text, trace = self.executive.process_request(
                user_text,
                user_id=session.user_id,
                collect_trace=True,
                force_agent=interaction.metadata.get("force_agent", False)
            )
        else:
            # For non-text interactions, we might need a different handling.
            # For now, treat as text.
            response_text = f"Received {interaction.kind} interaction. Processing not fully implemented."
            trace = None

        # Store user message and assistant response in session
        user_msg = Message(role=MessageRole.USER, content=str(interaction.content))
        assistant_msg = Message(role=MessageRole.ASSISTANT, content=response_text)
        self.session_manager.add_message(session.session_id, user_msg)
        self.session_manager.add_message(session.session_id, assistant_msg)

        # Update session state back to idle
        self.session_manager.update_state(session.session_id, "idle")

        # Build response
        resp = InteractionResponse(
            text=response_text,
            markdown=response_text,  # Assume markdown-compatible for now
            trace=trace,
        )
        return resp

    def process_interaction_stream(self, interaction: Interaction) -> Generator[str, None, None]:
        """
        Process interaction and stream response tokens.
        Currently, ExecutiveMind returns a full response; we simulate streaming.
        In future, we can integrate with a streaming LLM.
        """
        # For now, just yield the full response in chunks.
        response = self.process_interaction(interaction)
        text = response.text
        if text:
            # Simulate streaming by splitting into words
            words = text.split()
            for i in range(0, len(words), 5):
                chunk = " ".join(words[i:i+5])
                yield f"{chunk} "
            yield "\n"
        else:
            yield "No response generated."

    def handle_interruption(self, session_id: UUID) -> bool:
        """Abort ongoing processing for a session."""
        # In future, we can cancel tasks.
        logger.info(f"[ConversationEngine] Interruption requested for session {session_id}")
        return True
