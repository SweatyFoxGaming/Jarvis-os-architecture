import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.cognition.models import WorkspaceContents, KnowledgeItem
from src.core.models import Goal, Task

logger = logging.getLogger(__name__)


class CognitiveWorkspace:
    """
    The current "mind" of Jarvis – the short‑term, high‑availability working set.
    """

    def __init__(self):
        self._contents = WorkspaceContents()
        logger.info("[CognitiveWorkspace] Initialized.")

    def set_goal(self, goal: Goal) -> None:
        self._contents.goal = goal
        self._contents.timestamp = datetime.now()
        logger.debug(f"[CognitiveWorkspace] Goal set: {goal.title}")

    def set_task(self, task: Task) -> None:
        self._contents.task = task
        self._contents.timestamp = datetime.now()
        logger.debug(f"[CognitiveWorkspace] Task set: {task.target_capability}")

    def add_conversation_entry(self, role: str, content: str) -> None:
        self._contents.conversation.append({"role": role, "content": content})
        # Limit to last 20 entries to keep workspace manageable
        if len(self._contents.conversation) > 20:
            self._contents.conversation = self._contents.conversation[-20:]
        self._contents.timestamp = datetime.now()

    def add_memory(self, memory: KnowledgeItem) -> None:
        self._contents.memories.append(memory)
        # Limit to 10 memories
        if len(self._contents.memories) > 10:
            self._contents.memories = self._contents.memories[-10:]

    def add_capability_result(self, capability_name: str, result: Any) -> None:
        self._contents.capability_results[capability_name] = result
        self._contents.timestamp = datetime.now()

    def add_planner_note(self, note: str) -> None:
        self._contents.planner_notes.append(note)
        # Keep last 10 notes
        if len(self._contents.planner_notes) > 10:
            self._contents.planner_notes = self._contents.planner_notes[-10:]

    def add_reasoning_note(self, note: str) -> None:
        self._contents.reasoning_notes.append(note)
        if len(self._contents.reasoning_notes) > 10:
            self._contents.reasoning_notes = self._contents.reasoning_notes[-10:]

    def add_insight(self, insight: str) -> None:
        self._contents.insights.append(insight)
        if len(self._contents.insights) > 10:
            self._contents.insights = self._contents.insights[-10:]

    def add_hypothesis(self, hypothesis: str) -> None:
        self._contents.hypotheses.append(hypothesis)
        if len(self._contents.hypotheses) > 10:
            self._contents.hypotheses = self._contents.hypotheses[-10:]

    def set_budget(self, budget: Dict[str, Any]) -> None:
        self._contents.budget = budget

    def set_execution_context(self, context: Dict[str, Any]) -> None:
        self._contents.execution_context = context

    def get_contents(self) -> WorkspaceContents:
        return self._contents

    def clear(self) -> None:
        self._contents = WorkspaceContents()
        logger.debug("[CognitiveWorkspace] Cleared.")

    def reset_conversation(self) -> None:
        self._contents.conversation = []
        self._contents.timestamp = datetime.now()
