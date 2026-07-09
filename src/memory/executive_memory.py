from typing import List, Dict, Any
from src.core.models import ExecutiveDecision, Goal, MemoryRecord
from src.memory.tiered_memory import HierarchicalMemory

class ExecutiveMemory:
    """
    New memory system dedicated to executive reasoning.
    Separate from conversational memory.
    """
    def __init__(self, base_memory: HierarchicalMemory):
        self.memory = base_memory

    def record_decision(self, decision: ExecutiveDecision):
        record = MemoryRecord(
            source="ExecutiveMind",
            content=decision.dict(),
            importance=0.9,
            tags=["executive_decision", "strategy"]
        )
        self.memory.executive.store(record)

    def record_lesson(self, lesson: str, outcome_success: bool):
        record = MemoryRecord(
            source="SelfImprovement",
            content={"lesson": lesson, "success": outcome_success},
            importance=0.8,
            tags=["executive_lesson"]
        )
        self.memory.executive.store(record)

    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        records = self.memory.executive.records[-limit:]
        return [r.content for r in records]
