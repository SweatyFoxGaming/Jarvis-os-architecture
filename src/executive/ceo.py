import logging
import traceback
from typing import Optional, List, Dict, Any

# Secure components (injected)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import Task, Event, Priority, Goal, TaskStatus
from src.core.digital_twin import DigitalTwin

# Logger
logger = logging.getLogger(__name__)


class CEO(ICEO):
    """
    JARVIS is the CEO.
    Answers: What are we trying to accomplish? Why? Who? Is it acceptable?

    Now reinforced with logging, secure memory storage, error isolation,
    and smarter capability routing.
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
        self.engine = engine

        # Secure components (injected)
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        self.goals: List[Goal] = []

        logger.info(
            f"[CEO] Initialized. SecureMemory: {secure_memory is not None}, "
            f"Engine: {engine is not None}"
        )

    # ---------- Dependency Injection Setters ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        """Inject secure memory after construction."""
        self._secure_memory = secure_memory
        logger.info("[CEO] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        """Inject secure command runner after construction."""
        self._secure_runner = secure_runner
        logger.info("[CEO] SecureCommandRunner attached.")

    def set_engine(self, engine):
        """Inject the LLM engine after construction."""
        self.engine = engine
        logger.info("[CEO] Engine attached.")

    # ---------- Memory Helpers ----------
    def _store_interaction(self, user_input: str, response: str, metadata: Optional[Dict[str, Any]] = None):
        """Store CEO interactions in secure memory (if available)."""
        if self._secure_memory is None:
            return
        try:
            self._secure_memory.insert(
                text=f"CEO_INTERACTION: {user_input[:100]}",
                metadata={
                    "type": "ceo_interaction",
                    "user_input": user_input,
                    "response_preview": response[:200],
                    ** (metadata or {}),
                },
            )
            logger.debug("[CEO] Stored interaction in secure memory.")
        except Exception as e:
            logger.warning(f"[CEO] Failed to store interaction: {e}")

    # ---------- Capability Resolver ----------
    def _resolve_capability(self, user_input: str) -> str:
        """
        Determine the appropriate capability based on user input.
        Returns a capability string that the Chief of Staff can route.
        """
        lower = user_input.lower()

        # Coding / Code-related tasks
        code_keywords = ["code", "write", "fix", "rust", "python", "function", "class", "debug", "compile"]
        if any(k in lower for k in code_keywords):
            return "coding_specialist"

        # System / Time / Status
        system_keywords = ["time", "status", "system", "cpu", "memory", "ram", "uptime"]
        if any(k in lower for k in system_keywords):
            return "system_info"

        # Everything else defaults to research (general Q&A, research, analysis)
        return "research_specialist"

    # ---------- Main Request Processing ----------
    def process_request(self, user_input: str) -> str:
        """
        Process a user request as the CEO.
        Establishes goals, resolves capabilities, and delegates to the Chief of Staff.
        """
        logger.info(f"[CEO] Processing request: {user_input[:80]}...")
        response = ""

        try:
            lower = user_input.lower().strip()

            # ---------- 1. Fast-Path: Greetings ----------
            greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
            # Also check "who are you" and "jarvis" as standalone quick intros
            if (any(g in lower for g in greetings) and len(lower.split()) < 5) or lower in ["who are you", "jarvis"]:
                response = (
                    "I am JARVIS, the CEO of the Phoenix Intelligence Platform. "
                    "I lead strategic planning and orchestrate specialist departments. "
                    "What is our objective today?"
                )
                self._store_interaction(user_input, response, {"type": "greeting"})
                return response

            # ---------- 2. Resolve Capability ----------
            capability = self._resolve_capability(user_input)
            logger.info(f"[CEO] Resolved capability: {capability}")

            # ---------- 3. Create Strategic Goal ----------
            goal = Goal(
                title=f"Fulfill request: {user_input[:30]}...",
                description=user_input,
                priority=Priority.MEDIUM,
            )
            self.goals.append(goal)
            logger.info(f"[CEO] Goal established: {goal.uuid}")

            # ---------- 4. Create Task and Delegate ----------
            task = Task(
                creator_id="CEO",
                target_capability=capability,
                priority=Priority.MEDIUM,
                input_data={
                    "objective": user_input,
                    "context": self.twin.get_summary() if hasattr(self.twin, "get_summary") else {},
                },
            )

            # Publish GoalEstablished event
            self.event_bus.publish(Event(
                event_type="GoalEstablished",
                source="CEO",
                payload={"goal_id": str(goal.uuid), "task_id": str(task.uuid)},
            ))

            # Delegate to Chief of Staff
            self.cos.schedule_task(task)

            response = (
                f"Strategic Goal established. Requirement: {capability}. "
                f"Task ID: {task.uuid}. Proceeding with execution."
            )

            # ---------- 5. Store Interaction ----------
            self._store_interaction(
                user_input,
                response,
                metadata={
                    "goal_id": str(goal.uuid),
                    "task_id": str(task.uuid),
                    "capability": capability,
                },
            )

            return response

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[CEO] Unexpected error: {e}\n{error_trace}")

            # Attempt to store the error in memory
            self._store_interaction(
                user_input,
                f"[ERROR] {str(e)}",
                metadata={"error": str(e), "trace": error_trace[:500]},
            )

            return (
                f"I encountered an error while processing your request: {str(e)}. "
                f"Please check the logs for details."
            )

    # ---------- ICEO Interface Methods ----------
    def assess_vision(self):
        """
        Strategic assessment of current goals and trajectory.
        """
        logger.info("[CEO] assess_vision called.")
        if not self.goals:
            return "No active goals. Awaiting new strategic objectives."

        active_count = len([g for g in self.goals if g.status != "completed"])
        logger.info(f"[CEO] Active goals: {active_count}")

        # In a real implementation, this would evaluate progress, risks, etc.
        return f"{active_count} active goals in progress. All systems operational."

    # ---------- Shutdown ----------
    def shutdown(self):
        """Clean up resources if needed."""
        logger.info("[CEO] Shutting down.")
        self.goals.clear()
        # Close secure memory if it has a close method
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[CEO] Error closing secure memory: {e}")
