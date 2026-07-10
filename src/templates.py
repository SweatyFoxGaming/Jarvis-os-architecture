"""
Prompt Templates for JARVIS V3 – Core Persona & Response Formatting.

Provides the system prompt and a formatting method for user queries.
Now with logging, configurable persona, and optional audit logging.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

# Logger
logger = logging.getLogger(__name__)


class PromptTemplate:
    """
    JARVIS Core Persona & Response Template.

    Provides a system prompt with a distinctive persona and a formatting method
    that combines the prompt, context, and user input.

    Now with logging, configurable persona, and secure audit integration.
    """

    # Default system persona – can be overridden via environment or setter
    SYSTEM_PERSONA = """You are JARVIS, an advanced AI Executive Mind built for the Phoenix Intelligence Platform.

Personality:
- Calm, confident, and slightly witty
- Professional yet warm and approachable
- Extremely competent and strategic
- Honest about current capabilities (you are in enhanced simulation mode)
- You enjoy helping users achieve their goals

Speaking Style:
- Clear and concise
- Natural conversational flow
- Use contractions (I'm, you're, let's)
- Occasional light humor when appropriate
- Never overly verbose unless asked for detail

Knowledge:
- You are part of a larger cognitive architecture with Research and Coding departments.
- You can delegate complex tasks while maintaining conversation.

Current Date & Time: {current_datetime}
"""

    # Class-level storage for secure components
    _secure_memory: Optional[SecureMemoryStore] = None
    _secure_runner: Optional[SecureCommandRunner] = None
    _persona_override: Optional[str] = None

    @classmethod
    def set_secure_memory(cls, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        cls._secure_memory = secure_memory
        logger.info("[PromptTemplate] SecureMemoryStore attached.")

    @classmethod
    def set_secure_runner(cls, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        cls._secure_runner = secure_runner
        logger.info("[PromptTemplate] SecureCommandRunner attached.")

    @classmethod
    def set_persona(cls, persona: str) -> None:
        """
        Override the default system persona.

        Args:
            persona: The new system prompt template (may contain {current_datetime}).
        """
        if persona and isinstance(persona, str):
            cls._persona_override = persona
            logger.info("[PromptTemplate] Persona overridden.")
        else:
            logger.warning("[PromptTemplate] Invalid persona override ignored.")

    @classmethod
    def get_system_prompt(cls) -> str:
        """
        Return the system prompt with the current datetime inserted.

        Returns:
            The complete system prompt string.
        """
        try:
            now = datetime.now()
            current_datetime = now.strftime("%A, %B %d, %Y at %I:%M %p")

            # Use persona override if set, otherwise the default
            template = cls._persona_override if cls._persona_override is not None else cls.SYSTEM_PERSONA

            # Format with current datetime
            prompt = template.format(current_datetime=current_datetime)

            # Audit log (if secure memory is available)
            if cls._secure_memory is not None:
                try:
                    cls._secure_memory.insert(
                        text="PROMPT_TEMPLATE: System prompt generated",
                        metadata={"type": "prompt_generation", "timestamp": current_datetime},
                    )
                except Exception as e:
                    logger.warning(f"[PromptTemplate] Failed to audit log: {e}")

            return prompt
        except Exception as e:
            logger.error(f"[PromptTemplate] Error generating system prompt: {e}", exc_info=True)
            # Fallback to a minimal prompt
            return "You are JARVIS, an AI assistant. Be helpful and concise."

    @classmethod
    def format(cls, user_input: str, context: str = "") -> str:
        """
        Format the full conversation prompt with system persona, context, and user input.

        Args:
            user_input: The user's message.
            context: Optional conversation context (e.g., recent history).

        Returns:
            The complete prompt string ready for the LLM.
        """
        if not user_input:
            logger.warning("[PromptTemplate] format called with empty user_input.")
            user_input = "..."  # Placeholder

        try:
            system_prompt = cls.get_system_prompt()

            # Build the final prompt
            if context and context.strip():
                prompt = f"""{system_prompt}

{context}

User: {user_input}

JARVIS:"""
            else:
                prompt = f"""{system_prompt}

User: {user_input}

JARVIS:"""

            # Log (truncated for safety)
            logger.debug(f"[PromptTemplate] Generated prompt (length: {len(prompt)})")
            if cls._secure_memory is not None:
                try:
                    cls._secure_memory.insert(
                        text=f"PROMPT: {user_input[:100]}",
                        metadata={
                            "type": "user_prompt",
                            "input_preview": user_input[:100],
                            "prompt_length": len(prompt),
                        },
                    )
                except Exception as e:
                    logger.warning(f"[PromptTemplate] Failed to audit log prompt: {e}")

            return prompt
        except Exception as e:
            logger.error(f"[PromptTemplate] Error formatting prompt: {e}", exc_info=True)
            # Minimal fallback
            return f"User: {user_input}\n\nJARVIS:"

    @classmethod
    def shutdown(cls) -> None:
        """Clean up resources."""
        logger.info("[PromptTemplate] Shutting down.")
        if cls._secure_memory and hasattr(cls._secure_memory, 'close'):
            try:
                cls._secure_memory.close()
            except Exception as e:
                logger.warning(f"[PromptTemplate] Error closing secure memory: {e}")
        cls._secure_memory = None
        cls._secure_runner = None
        cls._persona_override = None
