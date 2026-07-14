"""
Delegation – direct other systems to perform work.
Now synchronous: executes tasks and returns results.
"""

import logging
from typing import Dict, Any, Optional

from src.executive.chief_of_staff import ChiefOfStaff
from src.core.models import Task

logger = logging.getLogger(__name__)


class DelegationManager:
    """
    Delegates work to the Execution Platform.
    Now executes tasks synchronously and returns the result.
    """

    def __init__(self, chief_of_staff: ChiefOfStaff):
        self.cos = chief_of_staff
        self._delegated_tasks: Dict[str, Dict[str, Any]] = {}
        logger.info("[DelegationManager] Initialized (synchronous mode).")

    def delegate_task(self, task: Task, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Delegate a Task to the Execution Platform and execute it synchronously.
        Returns the result of the capability execution.
        Raises an exception if the execution fails.
        """
        logger.info(f"[DelegationManager] Delegating task {task.uuid} for capability {task.target_capability}")

        try:
            # Execute the task synchronously via ChiefOfStaff
            result = self.cos.schedule_task(task)
            # Store the delegation record
            self._delegated_tasks[str(task.uuid)] = {
                "task": task,
                "status": "completed",
                "result": result,
                "context": context or {},
            }
            logger.info(f"[DelegationManager] Task {task.uuid} completed successfully.")
            return result
        except Exception as e:
            logger.error(f"[DelegationManager] Delegation failed for task {task.uuid}: {e}")
            self._delegated_tasks[str(task.uuid)] = {
                "task": task,
                "status": "failed",
                "error": str(e),
                "context": context or {},
            }
            # Re-raise the exception so the caller (e.g., ExecutiveMind) can handle it
            raise

    def get_delegated_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the record of a delegated task."""
        return self._delegated_tasks.get(task_id)

    def update_delegated_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """Update the status and optionally the result of a delegated task."""
        if task_id in self._delegated_tasks:
            self._delegated_tasks[task_id]["status"] = status
            if result is not None:
                self._delegated_tasks[task_id]["result"] = result
            return True
        return False

    def get_all_delegated(self) -> Dict[str, Dict[str, Any]]:
        """Return all delegated tasks and their records."""
        return self._delegated_tasks
