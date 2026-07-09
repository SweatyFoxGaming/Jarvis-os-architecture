from typing import List, Optional, Any
from src.core.models import MemoryRecord

class MemoryTier:
    def __init__(self, name: str):
        self.name = name
        self.records: List[MemoryRecord] = []

    def store(self, record: MemoryRecord):
        self.records.append(record)

    def retrieve(self, query: str, limit: int = 5) -> List[MemoryRecord]:
        # Simple keyword search for MVP
        results = [r for r in self.records if query.lower() in str(r.content).lower()]
        return results[:limit]

class HierarchicalMemory:
    def __init__(self):
        self.working = MemoryTier("Working")
        self.episodic = MemoryTier("Episodic")
        self.semantic = MemoryTier("Semantic")
        self.procedural = MemoryTier("Procedural")

    def store_episode(self, content: Any, importance: float = 0.5):
        record = MemoryRecord(source="system", content=content, importance=importance)
        self.episodic.store(record)

    def retrieve_all_tiers(self, query: str) -> List[MemoryRecord]:
        results = []
        results.extend(self.working.retrieve(query))
        results.extend(self.episodic.retrieve(query))
        results.extend(self.semantic.retrieve(query))
        return results
