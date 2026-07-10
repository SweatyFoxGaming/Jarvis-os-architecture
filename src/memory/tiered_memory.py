from typing import List, Optional, Any, Dict
from src.core.models import MemoryRecord
from datetime import datetime

class MemoryTier:
    def __init__(self, name: str):
        self.name = name
        self.records: List[MemoryRecord] = []

    def store(self, record: MemoryRecord):
        self.records.append(record)
        print(f"[Memory] Stored in {self.name} tier")

    def retrieve(self, query: str, limit: int = 5) -> List[MemoryRecord]:
        results = [r for r in self.records if query.lower() in str(r.content).lower()]
        return results[-limit:]

class HierarchicalMemory:
    def __init__(self):
        self.working = MemoryTier("Working")
        self.episodic = MemoryTier("Episodic")
        self.semantic = MemoryTier("Semantic")
        
    def store_conversation(self, user_input: str, response: str):
        record = MemoryRecord(
            source="conversation",
            content={"user": user_input, "jarvis": response},
            importance=0.7,
            tags=["conversation"]
        )
        self.episodic.store(record)
        
    def get_recent_context(self, limit: int = 3) -> str:
        recent = self.episodic.records[-limit:]
        if not recent:
            return ""
        context = "Recent conversation:\n"
        for r in recent:
            context += f"User: {r.content['user']}\nJARVIS: {r.content['jarvis']}\n\n"
        return context
