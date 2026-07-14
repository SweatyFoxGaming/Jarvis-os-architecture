"""
Delegation – direct other systems to perform work.
"""

import logging
from typing import Dict, Any, Optional

from src.executive.chief_of_staff import ChiefOfStaff
from src.core.models import Task

logger = logging.getLogger(__name__)


class DelegationManager:
    """
    Delegates work to the Capability and Execution Platforms.
    """

    def __init__(self, chief_of_staff: ChiefOfStaff):
        self.cos = chief_of_staff
        self._delegated_tasks: Dict[str, Dict[str, Any]] = {}
        logger.info("[DelegationManager] Initialized.")

    def delegate_task(self, task: Task, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Delegate a Task to the Execution Platform.
        """
        logger.info(f"[DelegationManager] Delegating task {task.uuid} for capability {task.target_capability}")

        try:
            self.cos.schedule_task(task)
            self._delegated_tasks[str(task.uuid)] = {
                "task": task,
                "status": "delegated",
                "context": context or {},
            }
            logger.info(f"[DelegationManager] Task {task.uuid} delegated successfully.")
            return True
        except Exception as e:
            logger.error(f"[DelegationManager] Delegation failed for task {task.uuid}: {e}")
            return False

    def get_delegated_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._delegated_tasks.get(task_id)

    def update_delegated_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> bool:
        if task_id in self._delegated_tasks:
            self._delegated_tasks[task_id]["status"] = status
            if result:
                self._delegated_tasks[task_id]["result"] = result
            return True
        return False

    def get_all_delegated(self) -> Dict[str, Dict[str, Any]]:
        return self._delegated_tasks
