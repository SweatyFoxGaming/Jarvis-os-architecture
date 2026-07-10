import logging
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime

# Your existing interfaces and models
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard
from src.templates import PromptTemplate

# Legacy memory (kept for backward compatibility)
from src.memory.tiered_memory import HierarchicalMemory

# Secure components (will be injected)
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


class ExecutiveMind(ICEO):
    """
    JARVIS Executive Mind - Natural conversation + Memory
    Now reinforced with secure SQLite memory, logging, and error handling.
    """

    def __init__(
        self,
        chief_of_staff: IChiefOfStaff,
        event_bus: IEventBus,
        digital_twin: DigitalTwin,
        engine=None,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()

        # Engine (if available)
        self.engine = engine

        # Secure components (injected or None)
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        # Legacy memory (fallback if secure memory is not available)
        self.memory = HierarchicalMemory() if secure_memory is None else None

        self.active_goals: List[Goal] = []

        logger.info(
            f"[ExecutiveMind] Initialized. SecureMemory: {secure_memory is not None}, "
            f"Engine: {engine is not None and getattr(engine, 'llm', None) is not None}"
        )

    # ---------- Dependency Injection Setters (called by v2_main) ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        """Inject secure memory after construction."""
        self._secure_memory = secure_memory
        # If we were using fallback memory, we can now switch to secure
        if self.memory is not None and secure_memory is not None:
            logger.info("[ExecutiveMind] Switching from legacy memory to secure memory.")
            self.memory = None  # Stop using legacy
        logger.info("[ExecutiveMind] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        """Inject secure command runner after construction."""
        self._secure_runner = secure_runner
        logger.info("[ExecutiveMind] SecureCommandRunner attached.")

    def set_engine(self, engine):
        """Set the LLM engine (if not provided at init)."""
        self.engine = engine
        logger.info("[ExecutiveMind] Engine attached.")

    # ---------- Memory Helpers ----------
    def _get_recent_context(self, limit: int = 5) -> str:
        """
        Retrieve recent conversation history from secure memory.
        Falls back to legacy HierarchicalMemory if secure memory is not available.
        """
        if self._secure_memory is not None:
            try:
                # Search for conversation entries (type = "conversation")
                # We'll store conversations with metadata {"type": "conversation"}
                results = self._secure_memory.search_by_text("", limit=limit * 2)  # We'll filter later
                # Filter those with metadata.type == "conversation"
                convs = []
                for rec in results:
                    meta = rec.get("metadata", {})
                    if meta.get("type") == "conversation":
                        convs.append(rec)
                # Build context string from most recent
                context_lines = []
                for rec in convs[-limit:]:  # last 'limit' conversations
                    text = rec.get("text", "")
                    # text format: "CONVERSATION: user: ... | assistant: ..."
                    context_lines.append(text)
                if context_lines:
                    return "\n".join(context_lines)
                else:
                    return "No recent conversation history."
            except Exception as e:
                logger.warning(f"[ExecutiveMind] Failed to retrieve recent context from secure memory: {e}")
                # Fall through to legacy memory
        # Legacy fallback
        if self.memory is not None:
            try:
                return self.memory.get_recent_context()
            except Exception as e:
                logger.warning(f"[ExecutiveMind] Failed to retrieve context from legacy memory: {e}")
        return "No recent context available."

    def _store_conversation(self, user_input: str, response: str):
        """Store the conversation turn in secure memory (and legacy if present)."""
        timestamp = datetime.now().isoformat()
        # Store in secure memory
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"CONVERSATION: user: {user_input} | assistant: {response[:200]}",
                    metadata={
                        "type": "conversation",
                        "user_input": user_input,
                        "response_preview": response[:200],
                        "timestamp": timestamp,
                    },
                )
                logger.debug("[ExecutiveMind] Stored conversation in secure memory.")
            except Exception as e:
                logger.warning(f"[ExecutiveMind] Failed to store conversation in secure memory: {e}")
        # Also store in legacy memory if present
        if self.memory is not None:
            try:
                self.memory.store_conversation(user_input, response)
            except Exception as e:
                logger.warning(f"[ExecutiveMind] Failed to store conversation in legacy memory: {e}")

    # ---------- Main Request Processing ----------
    def process_request(self, user_input: str) -> str:
        """
        Process a user request, generate a response, and store in memory.
        """
        logger.info(f"[ExecutiveMind] Processing: {user_input[:80]}...")
        response = ""

        try:
            lower = user_input.lower().strip()

            # ---------- 1. Fast Path: Direct commands ----------
            if any(g in lower for g in ["hello", "hi", "hey"]):
                response = "Hello! Good to see you again. What can I do for you?"
            elif "how are you" in lower or "status" in lower:
                response = "I'm doing well, thanks for asking. Ready to help."
            elif "time" in lower:
                response = f"The current time is {datetime.now().strftime('%I:%M %p')}."
            else:
                # ---------- 2. LLM Path (if available) ----------
                if self.engine is not None and getattr(self.engine, 'llm', None) is not None:
                    # Build context from secure memory
                    context = self._get_recent_context()
                    formatted_prompt = PromptTemplate.format(user_input, context)

                    logger.debug(f"[ExecutiveMind] Generating LLM response for: {user_input[:50]}...")
                    response = self.engine.generate(
                        formatted_prompt,
                        max_tokens=512,
                        temperature=0.7,
                        stream=False,
                    )
                    # Check for error in response
                    if response.startswith("[ERROR]") or "failed" in response.lower():
                        logger.warning(f"[ExecutiveMind] LLM returned error: {response}")
                        # Use a fallback response
                        response = (
                            f"I encountered an issue processing your request. "
                            f"Please try again later or phrase your question differently."
                        )
                else:
                    # ---------- 3. No LLM: Use template ----------
                    logger.info("[ExecutiveMind] No LLM available, using template response.")
                    context = self._get_recent_context()
                    response = PromptTemplate.format(user_input, context)

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[ExecutiveMind] Unexpected error: {e}\n{error_trace}")
            response = (
                f"I'm sorry, an unexpected error occurred while processing your request. "
                f"Please check the logs for details."
            )

        # ---------- 4. Store conversation in memory ----------
        self._store_conversation(user_input, response)

        return response

    # ---------- Other ICEO methods (placeholder) ----------
    def assess_vision(self):
        """Placeholder for future implementation."""
        logger.debug("[ExecutiveMind] assess_vision called (not implemented).")
        pass

    # ---------- Shutdown ----------
    def shutdown(self):
        """Clean up resources if needed."""
        logger.info("[ExecutiveMind] Shutting down.")
        # No explicit cleanup needed for secure memory, but we can close it if needed.
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[ExecutiveMind] Error closing secure memory: {e}")
