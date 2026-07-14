import logging
import json
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.cognition.models import KnowledgeItem, KnowledgeType, KnowledgeVerificationStatus
from src.memory.secure_store import SecureMemoryStore

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """
    Storage for Knowledge items (facts, procedures, preferences, etc.).
    Uses SecureMemoryStore as the underlying storage with a specific metadata format.
    """

    def __init__(self, secure_memory: SecureMemoryStore):
        self.secure_memory = secure_memory
        logger.info("[KnowledgeStore] Initialized.")

    def store(self, knowledge: KnowledgeItem) -> UUID:
        """
        Store a Knowledge item. If a similar item exists, merge or update it.
        Returns the UUID of the stored item.
        """
        # Check for existing similar knowledge (simplified deduplication)
        existing = self._find_similar(knowledge)
        if existing:
            # Update existing
            existing.confidence = max(existing.confidence, knowledge.confidence)
            existing.reinforcement_count += 1
            existing.updated_at = datetime.now()
            if knowledge.verification_status == KnowledgeVerificationStatus.VERIFIED_BY_HUMAN:
                existing.verification_status = KnowledgeVerificationStatus.VERIFIED_BY_HUMAN
            # Update the record in memory
            self._update_record(existing)
            logger.info(f"[KnowledgeStore] Updated existing knowledge: {existing.uuid}")
            return existing.uuid
        else:
            # Insert new
            self._insert_record(knowledge)
            logger.info(f"[KnowledgeStore] Stored new knowledge: {knowledge.uuid}")
            return knowledge.uuid

    def _find_similar(self, knowledge: KnowledgeItem) -> Optional[KnowledgeItem]:
        """
        Find a knowledge item with the same content (simplified).
        In a real system, we'd use embeddings for semantic similarity.
        """
        # For now, we search by text content using simple text search
        if isinstance(knowledge.content, str):
            results = self.secure_memory.search_by_text(knowledge.content, limit=5)
            for r in results:
                meta = r.get("metadata", {})
                if meta.get("type") == "knowledge" and meta.get("content") == knowledge.content:
                    return self._record_to_knowledge(r)
        return None

    def _insert_record(self, knowledge: KnowledgeItem) -> None:
        text = f"KNOWLEDGE: {knowledge.content}"
        if isinstance(knowledge.content, dict):
            text = f"KNOWLEDGE: {json.dumps(knowledge.content)}"
        metadata = {
            "type": "knowledge",
            "knowledge_type": knowledge.type.value,
            "content": knowledge.content,
            "confidence": knowledge.confidence,
            "verification_status": knowledge.verification_status.value,
            "source": knowledge.source.value if knowledge.source else None,
            "source_uuid": str(knowledge.source_uuid) if knowledge.source_uuid else None,
            "evidence": [str(e) for e in knowledge.evidence],
            "reinforcement_count": knowledge.reinforcement_count,
            "usage_count": knowledge.usage_count,
        }
        self.secure_memory.insert(text, metadata, user_id="system")

    def _update_record(self, knowledge: KnowledgeItem) -> None:
        # For simplicity, we delete and re-insert.
        # In production, we'd use an update query.
        # We'll use a simple approach: store as new and mark old as "deprecated"?
        # Since we have a simple store, we'll store a new version and rely on the search to find the latest.
        # But we'll just insert again and rely on deduplication logic.
        # For now, we delete old and insert new.
        # We need to find the old record ID first.
        results = self.secure_memory.search_by_text(str(knowledge.content), limit=10)
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("type") == "knowledge" and meta.get("content") == knowledge.content:
                self.secure_memory.delete_by_id(r["id"], user_id="system")
        self._insert_record(knowledge)

    def _record_to_knowledge(self, record: Dict[str, Any]) -> KnowledgeItem:
        meta = record.get("metadata", {})
        return KnowledgeItem(
            type=KnowledgeType(meta.get("knowledge_type", "fact")),
            content=meta.get("content", record.get("text", "")),
            confidence=meta.get("confidence", 0.5),
            verification_status=KnowledgeVerificationStatus(meta.get("verification_status", "unverified")),
            source=ExperienceSource(meta.get("source")) if meta.get("source") else None,
            source_uuid=UUID(meta.get("source_uuid")) if meta.get("source_uuid") else None,
            evidence=[UUID(e) for e in meta.get("evidence", []) if e],
            reinforcement_count=meta.get("reinforcement_count", 0),
            usage_count=meta.get("usage_count", 0),
            created_at=datetime.fromisoformat(meta.get("created_at")) if meta.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(meta.get("updated_at")) if meta.get("updated_at") else datetime.now(),
            last_used=datetime.fromisoformat(meta.get("last_used")) if meta.get("last_used") else None,
            metadata=meta.get("extra", {}),
        )

    def retrieve_for_context(self, query: str, limit: int = 5) -> List[KnowledgeItem]:
        """
        Retrieve knowledge items relevant to a given query.
        """
        results = self.secure_memory.search_by_text(query, limit=limit)
        knowledge_items = []
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("type") == "knowledge":
                knowledge_items.append(self._record_to_knowledge(r))
        return knowledge_items

    def get_by_uuid(self, uuid: UUID) -> Optional[KnowledgeItem]:
        """
        Retrieve a knowledge item by UUID.
        """
        results = self.secure_memory.search_by_text(str(uuid), limit=1)
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("type") == "knowledge" and meta.get("uuid") == str(uuid):
                return self._record_to_knowledge(r)
        return None

    def get_all(self, limit: int = 100) -> List[KnowledgeItem]:
        """
        Retrieve all knowledge items.
        """
        results = self.secure_memory.get_all(limit=limit, user_id="system")
        knowledge_items = []
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("type") == "knowledge":
                knowledge_items.append(self._record_to_knowledge(r))
        return knowledge_items

    def delete(self, uuid: UUID) -> bool:
        """
        Delete a knowledge item by UUID.
        """
        results = self.secure_memory.search_by_text(str(uuid), limit=1)
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("type") == "knowledge" and meta.get("uuid") == str(uuid):
                return self.secure_memory.delete_by_id(r["id"], user_id="system")
        return False
