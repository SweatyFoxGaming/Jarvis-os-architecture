import logging
import traceback
from typing import Optional, Dict, Any

from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


class ResearchWorker(BaseWorker):
    def __init__(self, worker_id: str, engine=None, secure_memory=None, secure_runner=None):
        super().__init__(worker_id)
        self.engine = engine
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner
        logger.info(f"[{worker_id}] Initialized with secure_memory={secure_memory is not None}")

    def execute(self, task: Task) -> Task:
        query = task.input_data.get("request") or task.input_data.get("objective", "")
        logger.info(f"[ResearchWorker] Processing: {query[:80]}...")

        try:
            if self.engine is None or self.engine.llm is None:
                response = "I am operating in simulation mode. The full cognitive system is active."
            else:
                prompt = f"""You are JARVIS, a calm, professional, and highly capable AI assistant.
You are the Executive Mind of the Phoenix Intelligence Platform.

User Query: {query}

Respond naturally and helpfully:"""
                response = self.engine.generate(prompt, max_tokens=768, temperature=0.7)

            task.output_data = {"report": response}
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
        except Exception as e:
            logger.error(f"[ResearchWorker] Error: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.output_data = {"error": str(e)}

        return task


class ResearchDepartment(BaseDepartment):
    def __init__(self, engine=None, secure_memory=None, secure_runner=None):
        super().__init__("Research")
        self.engine = engine
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner

    def initialize(self, event_bus):
        super().initialize(event_bus)
        worker = ResearchWorker(
            "research-worker-01",
            engine=self.engine,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )
        self.manager.register_worker(worker)
        logger.info("[Research] Department initialized and worker registered.")
