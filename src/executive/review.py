"""
Review – evaluate the results of execution.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.models import Goal, Task

logger = logging.getLogger(__name__)


class ReviewEngine:
    """
    Evaluates the results of execution.
    """

    def __init__(self):
        self._reviews: Dict[str, Dict[str, Any]] = {}
        logger.info("[ReviewEngine] Initialized.")

    def review_goal(self, goal: Goal, tasks: list) -> Dict[str, Any]:
        """
        Review a Goal and its associated Tasks.
        """
        logger.info(f"[ReviewEngine] Reviewing Goal {goal.uuid}")

        completed_tasks = [t for t in tasks if hasattr(t, 'state') and t.state.value == "completed"]
        failed_tasks = [t for t in tasks if hasattr(t, 'state') and t.state.value == "failed"]

        review = {
            "goal_uuid": str(goal.uuid),
            "goal_title": goal.title,
            "status": goal.state.value,
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "total_tasks": len(tasks),
            "success_rate": len(completed_tasks) / len(tasks) if tasks else 0,
            "summary": goal.result_summary or "No summary provided.",
            "timestamp": datetime.now().isoformat(),
        }

        self._reviews[str(goal.uuid)] = review
        logger.info(f"[ReviewEngine] Goal review completed: {goal.uuid} - {review['success_rate']:.2%} success rate")
        return review

    def review_task(self, task: Task) -> Dict[str, Any]:
        """
        Review a single Task.
        """
        logger.info(f"[ReviewEngine] Reviewing Task {task.uuid}")

        return {
            "task_uuid": str(task.uuid),
            "capability": task.target_capability,
            "status": task.state.value,
            "progress": task.progress,
            "output_preview": str(task.output_data)[:200] if task.output_data else None,
            "error": task.error_message,
            "timestamp": datetime.now().isoformat(),
        }

    def get_review(self, goal_uuid: str) -> Optional[Dict[str, Any]]:
        return self._reviews.get(goal_uuid)
