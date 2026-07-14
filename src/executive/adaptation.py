"""
Adaptation – change direction when conditions change.
"""

import logging
from typing import Dict, Any, List, Optional

from src.core.models import Goal, Task
from src.executive.state import ExecutiveState

logger = logging.getLogger(__name__)


class AdaptationEngine:
    """
    Adapts plans, strategies, and goals in response to changing conditions.
    """

    def __init__(self, state: ExecutiveState):
        self.state = state
        logger.info("[AdaptationEngine] Initialized.")

    def handle_task_failure(self, task: Task, error: str) -> List[Dict[str, Any]]:
        """
        Adapt to a task failure.
        Returns a list of proposed actions (replan, retry, escalate).
        """
        actions = []
        logger.info(f"[AdaptationEngine] Handling task failure: {task.uuid} - {error}")

        # Option 1: Retry if within budget
        if task.resource_budget and task.resource_budget.time_limit_sec > 0:
            actions.append({
                "action": "retry",
                "task_id": str(task.uuid),
                "reason": "Retrying within budget",
            })

        # Option 2: Replan (skip or replace)
        actions.append({
            "action": "replan",
            "task_id": str(task.uuid),
            "reason": "Task failed; need to find alternative",
        })

        # Option 3: Escalate to user
        actions.append({
            "action": "escalate",
            "task_id": str(task.uuid),
            "reason": f"Task failed with error: {error}",
        })

        # Record in state
        self.state.add_blocked_work(
            description=f"Task {task.uuid} failed",
            reason=error,
            context={"task_id": str(task.uuid), "actions": actions}
        )

        return actions

    def handle_budget_exceeded(self, goal: Goal) -> List[Dict[str, Any]]:
        """
        Adapt when a budget is exceeded.
        """
        actions = []
        logger.info(f"[AdaptationEngine] Budget exceeded for goal: {goal.uuid}")

        # Option 1: Reduce scope
        actions.append({
            "action": "reduce_scope",
            "goal_id": str(goal.uuid),
            "reason": "Budget exceeded; reducing scope",
        })

        # Option 2: Request additional budget
        actions.append({
            "action": "request_budget",
            "goal_id": str(goal.uuid),
            "reason": "Budget exceeded; requesting more",
        })

        return actions

    def handle_capability_unavailable(self, capability_name: str, task: Task) -> List[Dict[str, Any]]:
        """
        Adapt when a capability is unavailable.
        """
        actions = []
        logger.info(f"[AdaptationEngine] Capability unavailable: {capability_name}")

        # Try to find an alternative capability
        actions.append({
            "action": "find_alternative",
            "capability": capability_name,
            "task_id": str(task.uuid),
            "reason": f"Capability {capability_name} unavailable",
        })

        return actions

    def handle_user_feedback(self, feedback: str, goal: Optional[Goal] = None) -> List[Dict[str, Any]]:
        """
        Adapt based on user feedback.
        """
        actions = []
        logger.info(f"[AdaptationEngine] User feedback: {feedback}")

        if "stop" in feedback.lower():
            actions.append({
                "action": "cancel",
                "reason": "User requested stop",
            })
        elif "different" in feedback.lower() or "alternative" in feedback.lower():
            actions.append({
                "action": "replan",
                "reason": "User requested a different approach",
            })
        else:
            actions.append({
                "action": "continue",
                "reason": "Proceeding with current plan",
            })

        return actions
