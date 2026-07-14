"""
Executive State – tracks current responsibility, commitments, and decisions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from src.core.models import Goal, Task

logger = logging.getLogger(__name__)


class ExecutiveState:
    """
    Tracks the Executive's current operational and strategic state.
    Distinct from Knowledge Store – this is current responsibility, not learned knowledge.
    """

    def __init__(self):
        # Operational State
        self.active_goals: Dict[str, Goal] = {}
        self.running_tasks: Dict[str, Task] = {}
        self.blocked_work: List[Dict[str, Any]] = []
        self.delegated_work: List[Dict[str, Any]] = []
        self.resource_usage: Dict[str, Any] = {}

        # Strategic State
        self.long_term_objectives: List[Dict[str, Any]] = []
        self.commitments: List[Dict[str, Any]] = []
        self.deadlines: List[Dict[str, Any]] = []
        self.risk_register: List[Dict[str, Any]] = []
        self.major_decisions: List[Dict[str, Any]] = []
        self.resource_commitments: Dict[str, Any] = {}

        self._last_updated: datetime = datetime.now()
        logger.info("[ExecutiveState] Initialized.")

    def add_active_goal(self, goal: Goal) -> None:
        self.active_goals[str(goal.uuid)] = goal
        self._last_updated = datetime.now()

    def remove_active_goal(self, goal_id: str) -> None:
        if goal_id in self.active_goals:
            del self.active_goals[goal_id]
            self._last_updated = datetime.now()

    def get_active_goal(self, goal_id: str) -> Optional[Goal]:
        return self.active_goals.get(goal_id)

    def get_all_active_goals(self) -> List[Goal]:
        return list(self.active_goals.values())

    def add_running_task(self, task: Task) -> None:
        self.running_tasks[str(task.uuid)] = task
        self._last_updated = datetime.now()

    def remove_running_task(self, task_id: str) -> None:
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
            self._last_updated = datetime.now()

    def get_running_task(self, task_id: str) -> Optional[Task]:
        return self.running_tasks.get(task_id)

    def get_all_running_tasks(self) -> List[Task]:
        return list(self.running_tasks.values())

    def add_blocked_work(self, description: str, reason: str, context: Dict[str, Any]) -> None:
        self.blocked_work.append({
            "description": description,
            "reason": reason,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })
        self._last_updated = datetime.now()

    def resolve_blocked_work(self, index: int) -> None:
        if 0 <= index < len(self.blocked_work):
            self.blocked_work.pop(index)
            self._last_updated = datetime.now()

    def add_delegated_work(self, work: Dict[str, Any]) -> None:
        self.delegated_work.append(work)
        self._last_updated = datetime.now()

    def update_delegated_work(self, index: int, update: Dict[str, Any]) -> None:
        if 0 <= index < len(self.delegated_work):
            self.delegated_work[index].update(update)
            self._last_updated = datetime.now()

    def set_resource_usage(self, usage: Dict[str, Any]) -> None:
        self.resource_usage.update(usage)
        self._last_updated = datetime.now()

    def add_commitment(self, commitment: Dict[str, Any]) -> None:
        self.commitments.append(commitment)
        self._last_updated = datetime.now()

    def add_decision(self, decision: Dict[str, Any]) -> None:
        self.major_decisions.append(decision)
        self._last_updated = datetime.now()

    def add_to_risk_register(self, risk: Dict[str, Any]) -> None:
        self.risk_register.append(risk)
        self._last_updated = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        return {
            "active_goals": len(self.active_goals),
            "running_tasks": len(self.running_tasks),
            "blocked_work": len(self.blocked_work),
            "delegated_work": len(self.delegated_work),
            "commitments": len(self.commitments),
            "major_decisions": len(self.major_decisions),
            "risks": len(self.risk_register),
            "last_updated": self._last_updated.isoformat(),
        }

    def clear(self) -> None:
        self.active_goals = {}
        self.running_tasks = {}
        self.blocked_work = []
        self.delegated_work = []
        self.resource_usage = {}
        self.long_term_objectives = []
        self.commitments = []
        self.deadlines = []
        self.risk_register = []
        self.major_decisions = []
        self.resource_commitments = {}
        self._last_updated = datetime.now()
        logger.info("[ExecutiveState] Cleared.")
