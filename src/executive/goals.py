"""
Goal Management – convert Intent into actionable objectives.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from src.core.models import Goal, GoalBudget, Priority, ExecutionState
from src.executive.state import ExecutiveState

logger = logging.getLogger(__name__)


class GoalManager:
    """
    Manages the creation, lifecycle, and tracking of Goals.
    """

    def __init__(self, state: ExecutiveState):
        self.state = state
        self._goal_history: List[Goal] = []
        logger.info("[GoalManager] Initialized.")

    def create_goal_from_intent(
        self,
        intent: Dict[str, Any],
        user_id: str = "default",
        budget: Optional[GoalBudget] = None,
    ) -> Goal:
        """
        Create a Goal from a structured Intent.
        """
        title = intent.get("outcome", "Untitled Goal")[:100]
        description = intent.get("outcome", "")
        priority = self._map_urgency_to_priority(intent.get("urgency", "medium"))

        goal = Goal(
            title=title,
            description=description,
            user_id=user_id,
            budget=budget or GoalBudget(priority=priority),
        )
        self.state.add_active_goal(goal)
        self._goal_history.append(goal)
        logger.info(f"[GoalManager] Created Goal: {goal.uuid} - {goal.title}")
        return goal

    def update_goal_state(self, goal_id: str, new_state: ExecutionState) -> bool:
        """
        Update the state of a Goal.
        """
        goal = self.state.get_active_goal(goal_id)
        if not goal:
            logger.warning(f"[GoalManager] Goal {goal_id} not found.")
            return False
        goal.transition_to(new_state)
        if new_state == ExecutionState.COMPLETED:
            self.state.remove_active_goal(goal_id)
        logger.info(f"[GoalManager] Goal {goal_id} state updated to {new_state.value}")
        return True

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self.state.get_active_goal(goal_id)

    def get_all_active_goals(self) -> List[Goal]:
        return self.state.get_all_active_goals()

    def _map_urgency_to_priority(self, urgency: str) -> Priority:
        mapping = {
            "critical": Priority.URGENT,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
        }
        return mapping.get(urgency, Priority.MEDIUM)

    def get_goal_history(self, limit: int = 100) -> List[Goal]:
        return self._goal_history[-limit:]
