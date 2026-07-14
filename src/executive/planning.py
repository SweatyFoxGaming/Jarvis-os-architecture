"""
Planning – translate Strategy into coordinated work.
Extends the existing Planner with strategy-aware planning.
"""

import logging
from typing import List, Dict, Any, Optional

from src.execution.planner import Planner as BasePlanner
from src.core.models import Goal, Task
from src.core.registry import CapabilityRegistry
from src.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class PlanningEngine:
    """
    Translates Strategy into a detailed Plan.
    """

    def __init__(self, cap_registry: CapabilityRegistry, event_bus: EventBus):
        self.planner = BasePlanner(cap_registry, event_bus)
        logger.info("[PlanningEngine] Initialized.")

    def create_plan(self, goal: Goal, strategy: Dict[str, Any]) -> List[Task]:
        """
        Create a Plan from a Goal and Strategy.
        """
        logger.info(f"[PlanningEngine] Creating plan for Goal {goal.uuid} with strategy: {strategy.get('name', 'default')}")

        # Use the base planner to generate tasks
        tasks = self.planner.create_plan(goal)

        # Enhance tasks with strategy context
        for task in tasks:
            task.input_data["strategy"] = strategy.get("name", "default")
            task.input_data["strategy_description"] = strategy.get("description", "")

        logger.info(f"[PlanningEngine] Created {len(tasks)} tasks.")
        return tasks

    def create_plan_from_intent(self, intent: Dict[str, Any], strategy: Dict[str, Any]) -> List[Task]:
        """
        Create a Plan directly from an Intent and Strategy.
        """
        # Convert intent to a Goal first, then plan
        # In a full integration, we'd have a Goal Manager to do this.
        # For now, we create a temporary Goal.
        goal = Goal(
            title=intent.get("outcome", "Unknown Intent"),
            description=intent.get("outcome", ""),
            user_id=intent.get("user_id", "default"),
        )
        return self.create_plan(goal, strategy)
