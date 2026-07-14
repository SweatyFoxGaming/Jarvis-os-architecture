import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.cognition.models import KnowledgeItem, Belief, WorkspaceContents
from src.cognition.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


class RecallEngine:
    """
    Active memory API that provides suggestions, warnings, and contextual insights.
    """

    def __init__(self, knowledge_store: KnowledgeStore):
        self.knowledge_store = knowledge_store
        logger.info("[RecallEngine] Initialized.")

    def recall_for_context(self, context: Dict[str, Any], limit: int = 5) -> List[KnowledgeItem]:
        """
        Retrieve knowledge items relevant to the given context.
        """
        query = self._build_query(context)
        return self.knowledge_store.retrieve_for_context(query, limit)

    def _build_query(self, context: Dict[str, Any]) -> str:
        """
        Build a search query from context.
        """
        parts = []
        if context.get("goal"):
            parts.append(context["goal"])
        if context.get("task"):
            parts.append(context["task"])
        if context.get("user_input"):
            parts.append(context["user_input"])
        return " ".join(parts) if parts else ""

    def suggest_for_goal(self, goal_description: str) -> List[KnowledgeItem]:
        """
        Provide suggestions for a Goal based on past experiences.
        """
        return self.knowledge_store.retrieve_for_context(goal_description, limit=5)

    def warn_for_task(self, task_description: str) -> List[KnowledgeItem]:
        """
        Warn about potential issues for a Task.
        """
        # Retrieve knowledge about failures or warnings
        return self.knowledge_store.retrieve_for_context(f"failure warning {task_description}", limit=3)

    def get_confidence(self, claim: str) -> float:
        """
        Get the confidence of a claim based on Knowledge Store.
        """
        items = self.knowledge_store.retrieve_for_context(claim, limit=1)
        if items:
            return items[0].confidence
        return 0.0
