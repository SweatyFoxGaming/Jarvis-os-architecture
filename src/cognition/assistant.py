import logging
from typing import List, Optional, Dict, Any

from src.cognition.models import WorkspaceContents, KnowledgeItem
from src.cognition.recall import RecallEngine

logger = logging.getLogger(__name__)


class CognitiveAssistant:
    """
    The "subconscious" of Jarvis – constantly monitoring and offering suggestions.
    """

    def __init__(self, recall_engine: RecallEngine):
        self.recall = recall_engine
        logger.info("[CognitiveAssistant] Initialized.")

    def observe(self, workspace: WorkspaceContents) -> List[Dict[str, Any]]:
        """
        Observe the current Workspace and generate suggestions, warnings, reminders.
        Returns a list of observations.
        """
        observations = []

        goal = workspace.goal
        task = workspace.task

        if goal:
            # Suggest based on Goal
            suggestions = self.recall.suggest_for_goal(goal.description)
            for s in suggestions[:3]:
                observations.append({
                    "type": "suggestion",
                    "content": f"Consider: {s.content} (confidence: {s.confidence:.2f})",
                    "knowledge_uuid": str(s.uuid),
                })

            # Warn for potential pitfalls
            warnings = self.recall.warn_for_task(goal.description)
            for w in warnings[:2]:
                observations.append({
                    "type": "warning",
                    "content": f"Warning: {w.content} (confidence: {w.confidence:.2f})",
                    "knowledge_uuid": str(w.uuid),
                })

        if task:
            # Remind of past mistakes or successful strategies
            task_context = task.input_data.get("goal_description", "")
            reminders = self.recall.recall_for_context({"task": task_context}, limit=2)
            for r in reminders:
                observations.append({
                    "type": "reminder",
                    "content": f"Reminder: {r.content} (confidence: {r.confidence:.2f})",
                    "knowledge_uuid": str(r.uuid),
                })

        return observations
