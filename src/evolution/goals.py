"""
Evolution Platform – Engineering Goals.
"""

import logging
from typing import List, Optional
from uuid import UUID

from src.evolution.models import EngineeringGoal, GoalStatus
from src.evolution.repository import MetricsRepository

logger = logging.getLogger(__name__)


class GoalManager:
    """
    Manages engineering goals.
    """

    def __init__(self, repository: MetricsRepository):
        self.repository = repository

    def create_goal(self, title: str, description: str, target_metric: str, target_value: float) -> EngineeringGoal:
        """Create a new engineering goal."""
        goal = EngineeringGoal(
            title=title,
            description=description,
            target_metric=target_metric,
            target_value=target_value,
        )
        self.repository.save_goal(goal)
        logger.info(f"[GoalManager] Created goal: {title}")
        return goal

    def update_goal(self, goal_id: UUID, **kwargs) -> Optional[EngineeringGoal]:
        """Update an existing goal."""
        goal = self.repository.get_goal(goal_id)
        if not goal:
            return None
        for key, value in kwargs.items():
            if hasattr(goal, key):
                setattr(goal, key, value)
        goal.updated_at = datetime.now()
        self.repository.save_goal(goal)
        return goal

    def update_progress(self, goal_id: UUID, current_value: float) -> Optional[EngineeringGoal]:
        """Update the current progress of a goal."""
        goal = self.repository.get_goal(goal_id)
        if not goal:
            return None
        goal.current_value = current_value
        goal.updated_at = datetime.now()
        self.repository.save_goal(goal)
        return goal

    def list_goals(self, status: Optional[GoalStatus] = None) -> List[EngineeringGoal]:
        """List goals, optionally filtered by status."""
        return self.repository.get_goals(status)

    def delete_goal(self, goal_id: UUID) -> bool:
        return self.repository.delete_goal(goal_id)
