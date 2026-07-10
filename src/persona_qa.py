"""
JarvisQA – Core Q&A patterns for natural conversation.

Provides a simple yet extensible response generator for common queries.
Now with logging, intent detection, and optional secure memory audit.
"""

import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

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


class JarvisQA:
    """
    Core Q&A patterns for natural conversation.

    Provides responses for common phrases like greetings, status queries,
    time requests, and thanks. Can be extended with custom intents.
    """

    def __init__(
        self,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        """
        Initialize the Q&A engine.

        Args:
            secure_memory: Optional SecureMemoryStore for audit logging.
            secure_runner: Optional SecureCommandRunner (for future use).
        """
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        # Store the last processed intent for context
        self.last_intent: Optional[str] = None

        # Built-in responses (some are callable, some are lists)
        self._responses: Dict[str, Any] = {
            "greeting": [
                "Hello! JARVIS here. What can I do for you today?",
                "Good to see you. How can I assist?",
            ],
            "status": [
                "All systems are running smoothly. Executive architecture is fully active.",
                "I'm operating at peak performance. Ready for whatever you need.",
            ],
            "time": lambda: f"The current time is {datetime.now().strftime('%I:%M %p')}.",
            "thanks": [
                "You're very welcome.",
                "Always happy to help.",
            ],
            "goodbye": [
                "Goodbye! Let me know if you need anything else.",
                "See you later. I'll be here when you return.",
            ],
            "help": [
                "I can tell you the time, check system status, respond to greetings, or have a conversation.",
                "Just ask me anything — I'm here to assist.",
            ],
        }

        logger.info(
            f"[JarvisQA] Initialized with {len(self._responses)} intent patterns. "
            f"SecureMemory: {secure_memory is not None}"
        )

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info("[JarvisQA] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        self._secure_runner = secure_runner
        logger.info("[JarvisQA] SecureCommandRunner attached.")

    # ---------- Audit Helper ----------
    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Internal audit logging to secure memory."""
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"JARVIS_QA: {action} on {resource} - {status}",
                    metadata={
                        "type": "qa_audit",
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details or {},
                    },
                )
            except Exception as e:
                logger.warning(f"[JarvisQA] Failed to audit log: {e}")

    # ---------- Intent Detection ----------
    def detect_intent(self, text: str) -> str:
        """
        Detect the intent of a user message.

        Args:
            text: The user's input string.

        Returns:
            The intent key (e.g., "greeting", "status", "time", "thanks", "goodbye", "help").
            Defaults to "help" if no match.
        """
        if not text or not isinstance(text, str):
            logger.warning("[JarvisQA] detect_intent received invalid input.")
            return "help"

        lower = text.lower().strip()

        # Intent patterns (simple keyword matching)
        if any(k in lower for k in ["hello", "hi", "hey", "howdy", "greetings"]):
            return "greeting"
        elif any(k in lower for k in ["status", "how are you", "how's it going", "all systems"]):
            return "status"
        elif any(k in lower for k in ["time", "clock", "what time"]):
            return "time"
        elif any(k in lower for k in ["thanks", "thank you", "appreciate"]):
            return "thanks"
        elif any(k in lower for k in ["bye", "goodbye", "see you", "later"]):
            return "goodbye"
        elif any(k in lower for k in ["help", "what can you do", "capabilities"]):
            return "help"
        else:
            # If we have a previous intent, we could fallback to it, but default to "help"
            return "help"

    # ---------- Response Generation ----------
    def get_response(self, text: str) -> str:
        """
        Generate a response for a given user input.

        Args:
            text: The user's message.

        Returns:
            The response string.
        """
        if not text:
            return "I didn't catch that. Could you please repeat?"

        try:
            intent = self.detect_intent(text)
            self.last_intent = intent
            logger.debug(f"[JarvisQA] Detected intent: '{intent}' from text: {text[:50]}")

            # Retrieve the response handler
            handler = self._responses.get(intent)
            if handler is None:
                logger.warning(f"[JarvisQA] No handler for intent: {intent}")
                return "I'm not sure how to respond to that. Can you rephrase?"

            # If handler is a callable (lambda), call it
            if callable(handler):
                response = handler()
            # If handler is a list, pick one at random (or first)
            elif isinstance(handler, list):
                # In a real implementation, you might use random.choice
                # For deterministic behavior, pick the first
                response = handler[0]
            else:
                response = str(handler)

            self._audit_log("get_response", intent, "SUCCESS", {"text": text[:50], "response": response[:50]})
            return response

        except Exception as e:
            logger.error(f"[JarvisQA] Error generating response: {e}", exc_info=True)
            self._audit_log("get_response", "error", "FAILED", {"error": str(e)})
            return "I encountered an error while processing your request. Please try again."

    # ---------- Add Custom Intent ----------
    def add_intent(self, intent_key: str, handler: Any) -> None:
        """
        Add a new custom intent to the response system.

        Args:
            intent_key: The key to identify the intent.
            handler: A string (response), list of strings, or callable.
        """
        if not intent_key or not handler:
            raise ValueError("intent_key and handler must be provided.")

        self._responses[intent_key] = handler
        logger.info(f"[JarvisQA] Added custom intent: {intent_key}")

    # ---------- Get Last Intent ----------
    def get_last_intent(self) -> Optional[str]:
        """Return the last detected intent."""
        return self.last_intent

    # ---------- Shutdown ----------
    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("[JarvisQA] Shutting down.")
        self.last_intent = None
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[JarvisQA] Error closing secure memory: {e}")
        self._secure_memory = None
        self._secure_runner = None
