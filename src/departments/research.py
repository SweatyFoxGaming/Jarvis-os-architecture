import logging
import traceback
from typing import Optional, Dict, Any

# Secure components (will be injected)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

# Your existing base imports
from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

# Logger for this module
logger = logging.getLogger(__name__)


class ResearchWorker(BaseWorker):
    """
    Worker that handles general research, Q&A, and information retrieval.
    Secured with optional memory storage and command execution.
    """

    def __init__(
        self,
        worker_id: str,
        engine=None,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        super().__init__(worker_id)
        self.engine = engine
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner
        logger.info(f"[{worker_id}] Initialized with secure_memory={secure_memory is not None}")

    def _get_query(self, task: Task) -> str:
        """Safely extract the research query from task input."""
        query = task.input_data.get("request") or task.input_data.get("objective")
        if not query:
            query = task.input_data.get("text", "")  # fallback
        return str(query).strip()

    def _save_to_memory(self, query: str, response: str, metadata: Dict[str, Any]) -> None:
        """Store the interaction in the secure memory database (if available)."""
        if self.secure_memory is None:
            return
        try:
            self.secure_memory.insert(
                text=f"RESEARCH: {query}",
                metadata={
                    "type": "research_interaction",
                    "response_preview": response[:200],
                    **metadata,
                },
            )
            logger.debug(f"[{self.worker_id}] Stored research interaction in memory.")
        except Exception as e:
            logger.warning(f"[{self.worker_id}] Failed to store in memory: {e}")

    def execute(self, task: Task) -> Task:
        query = self._get_query(task)
        if not query:
            task.status = TaskStatus.FAILED
            task.output_data = {"error": "No research request or objective provided."}
            logger.warning(f"[{self.worker_id}] Task rejected: empty query.")
            return task

        logger.info(f"[{self.worker_id}] Processing research query: {query[:80]}...")

        try:
            # ---------- 1. SIMULATION MODE (fallback) ----------
            # Check if engine exists AND if the real model is loaded
            if self.engine is None or self.engine.llm is None:
                logger.info(f"[{self.worker_id}] Using simulation mode.")
                lower_query = query.lower()

                if "status" in lower_query or "who are you" in lower_query:
                    response = (
                        "I am JARVIS V3 — the Executive Mind of the Phoenix Intelligence Platform. "
                        "I am currently operating in **simulation mode** because the local LLM model is not loaded. "
                        "My cognitive architecture (Executive Mind, Board, and Departments) is fully active, "
                        "but responses are pre-scripted. To enable full autonomy, load a compatible .gguf model."
                    )
                elif "hello" in lower_query or "hi" in lower_query:
                    response = (
                        "Hello! I am JARVIS, your cognitive assistant. "
                        "I am ready to research, analyze, and assist. How may I help you today?"
                    )
                else:
                    response = (
                        f"[SIMULATION] I acknowledge your research query: '{query[:100]}...'. "
                        "In full mode, I would search my knowledge base, perform web research (via Brave API), "
                        "and synthesize a comprehensive report. Please load a real model or connect API keys."
                    )

            # ---------- 2. REAL LLM MODE ----------
            else:
                logger.info(f"[{self.worker_id}] Generating research response via LLM.")
                prompt = f"""You are JARVIS, a calm, professional, and highly capable AI assistant.
You are the Executive Mind of the Phoenix Intelligence Platform.

User Query: {query}

Respond naturally, helpfully, and with depth. If the query asks for research, provide a structured analysis."""

                response = self.engine.generate(
                    prompt,
                    max_tokens=768,       # Research answers need moderate length
                    temperature=0.7,       # Slightly creative but grounded
                    stream=False,
                )

                # If the response is an error string from the engine, treat it as failure
                if response.startswith("[ERROR]") or "failed" in response.lower():
                    raise RuntimeError(f"LLM engine returned an error: {response}")

            # ---------- 3. STORE IN SECURE MEMORY ----------
            self._save_to_memory(
                query=query,
                response=response,
                metadata={"worker_id": self.worker_id, "type": "research"},
            )

            # ---------- 4. SET TASK OUTPUT ----------
            task.output_data = {
                "report": response,
                "raw_response": response,  # for debugging
            }
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[{self.worker_id}] Task failed: {e}\n{error_trace}")
            task.status = TaskStatus.FAILED
            task.output_data = {
                "error": str(e),
                "trace": error_trace,
                "report": "// Error generating research report. Check logs.",
            }
            task.progress = 0.0

        return task


class ResearchDepartment(BaseDepartment):
    """
    Department responsible for general research, Q&A, and information synthesis.
    Accepts secure components via setters for dependency injection.
    """

    def __init__(self, engine=None):
        super().__init__("Research")
        self.engine = engine
        self._secure_memory: Optional[SecureMemoryStore] = None
        self._secure_runner: Optional[SecureCommandRunner] = None
        self._worker: Optional[ResearchWorker] = None

    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        """Dependency injection for secure memory (called by main.py)."""
        self._secure_memory = secure_memory
        if self._worker:
            self._worker.secure_memory = secure_memory
        logger.info(f"[{self.name}] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        """Dependency injection for secure command runner (called by main.py)."""
        self._secure_runner = secure_runner
        if self._worker:
            self._worker.secure_runner = secure_runner
        logger.info(f"[{self.name}] SecureCommandRunner attached.")

    def initialize(self, event_bus):
        super().initialize(event_bus)

        # Create the worker with the engine and any injected secure components
        self._worker = ResearchWorker(
            worker_id=f"{self.name.lower()}-worker-01",
            engine=self.engine,
            secure_memory=self._secure_memory,
            secure_runner=self._secure_runner,
        )
        self.manager.register_worker(self._worker)
        logger.info(f"[{self.name}] Department initialized and worker registered.")

    # Optional: Clean shutdown
    def shutdown(self):
        """Clean up resources if needed."""
        logger.info(f"[{self.name}] Shutting down.")
        self._worker = None
