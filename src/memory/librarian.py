"""
Knowledge Librarian – responsible for consolidating episodic memory,
detecting contradictions, and elevating important knowledge to semantic memory.

Part of the Phoenix Intelligence Platform's memory system.
"""

import logging
from typing import List, Optional, Dict, Any

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.core.models import MemoryRecord
from src.memory.tiered_memory import HierarchicalMemory

# Logger
logger = logging.getLogger(__name__)


class KnowledgeLibrarian:
    """
    Manages the consolidation of episodic memory into semantic memory,
    deduplication, and contradiction detection.

    Now with logging, error handling, and secure audit logging.
    """

    def __init__(
        self,
        memory: HierarchicalMemory,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        """
        Initialize the KnowledgeLibrarian.

        Args:
            memory: The HierarchicalMemory instance to manage.
            secure_memory: Optional SecureMemoryStore for audit logging.
            secure_runner: Optional SecureCommandRunner (for future use).
        """
        if memory is None:
            raise ValueError("memory cannot be None")

        self.memory = memory
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        logger.info(
            f"[KnowledgeLibrarian] Initialized. "
            f"SecureMemory: {secure_memory is not None}"
        )

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info("[KnowledgeLibrarian] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        self._secure_runner = secure_runner
        logger.info("[KnowledgeLibrarian] SecureCommandRunner attached.")

    # ---------- Audit Logging ----------
    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Internal audit logging to secure memory."""
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"KNOWLEDGE_LIBRARIAN: {action} on {resource} - {status}",
                    metadata={
                        "type": "knowledge_librarian_audit",
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details or {},
                    },
                )
            except Exception as e:
                logger.warning(f"[KnowledgeLibrarian] Failed to audit log: {e}")

    # ---------- Consolidation ----------
    def consolidate_episodes(self, min_importance: float = 0.8) -> int:
        """
        Consolidate episodic memory records into semantic memory.

        Records with importance >= min_importance and verification_status 'unverified'
        are promoted to semantic memory and marked as verified.

        Args:
            min_importance: Minimum importance score to promote a record.

        Returns:
            Number of records promoted.
        """
        logger.info("[KnowledgeLibrarian] Starting episodic consolidation...")
        promoted_count = 0

        try:
            # Check if episodic store exists
            if not hasattr(self.memory, 'episodic') or not hasattr(self.memory.episodic, 'records'):
                logger.warning("[KnowledgeLibrarian] Episodic memory store not available.")
                return 0

            records = self.memory.episodic.records
            if not records:
                logger.info("[KnowledgeLibrarian] No episodic records to consolidate.")
                return 0

            # Iterate over a copy of the list to allow modifications
            for record in records[:]:  # shallow copy
                try:
                    # Check if record qualifies for promotion
                    if (record.verification_status == "unverified" and
                        record.importance >= min_importance):

                        # Promote to semantic memory
                        self.memory.semantic.store(record)
                        record.verification_status = "verified"
                        promoted_count += 1
                        logger.debug(f"[KnowledgeLibrarian] Promoted record {record.uuid} to semantic memory.")

                        # Audit
                        self._audit_log(
                            "consolidate_episode",
                            str(record.uuid),
                            "PROMOTED",
                            {"importance": record.importance},
                        )

                except AttributeError as e:
                    logger.warning(f"[KnowledgeLibrarian] Record missing expected attribute: {e}")
                    continue
                except Exception as e:
                    logger.error(f"[KnowledgeLibrarian] Failed to promote record {record.uuid}: {e}", exc_info=True)

            logger.info(f"[KnowledgeLibrarian] Consolidation complete. Promoted {promoted_count} records.")
            self._audit_log("consolidate_episodes", "episodic_memory", "COMPLETED", {"promoted": promoted_count})
            return promoted_count

        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Consolidation failed: {e}", exc_info=True)
            self._audit_log("consolidate_episodes", "episodic_memory", "FAILED", {"error": str(e)})
            return 0

    # ---------- Contradiction Detection ----------
    def detect_contradictions(self, new_record: MemoryRecord) -> List[str]:
        """
        Check if a new record contradicts existing semantic memory.

        Args:
            new_record: The new MemoryRecord to check.

        Returns:
            List of conflict descriptions (empty if none).
        """
        if new_record is None:
            logger.warning("[KnowledgeLibrarian] detect_contradictions called with None record.")
            return []

        conflicts = []
        try:
            # Ensure semantic store exists
            if not hasattr(self.memory, 'semantic') or not hasattr(self.memory.semantic, 'records'):
                logger.warning("[KnowledgeLibrarian] Semantic memory store not available.")
                return []

            semantic_records = self.memory.semantic.records
            for existing in semantic_records:
                try:
                    # Simple placeholder: check if content is similar but contradicts
                    # For now, we just check if the new record's content is a string and existing content is a string
                    new_content = new_record.content
                    existing_content = existing.content

                    if isinstance(new_content, str) and isinstance(existing_content, str):
                        # Very primitive contradiction detection – words that are direct opposites
                        # This is a placeholder; in a real system you'd use embeddings or NLP.
                        if "not" in new_content and existing_content and "not" not in existing_content:
                            # Check if they are about the same topic (simple keyword overlap)
                            new_words = set(new_content.lower().split())
                            existing_words = set(existing_content.lower().split())
                            overlap = new_words.intersection(existing_words)
                            if len(overlap) > 3:  # heuristic
                                conflicts.append(f"Potential contradiction with record {existing.uuid}: '{existing_content[:50]}...'")
                except Exception as e:
                    logger.warning(f"[KnowledgeLibrarian] Error processing record {existing.uuid}: {e}")

            if conflicts:
                logger.info(f"[KnowledgeLibrarian] Detected {len(conflicts)} contradictions for record {new_record.uuid}.")
            else:
                logger.debug(f"[KnowledgeLibrarian] No contradictions detected for record {new_record.uuid}.")

            return conflicts

        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Contradiction detection failed: {e}", exc_info=True)
            return []

    # ---------- Deduplication ----------
    def deduplicate(self, similarity_threshold: float = 0.9) -> int:
        """
        Merge duplicate records in semantic and episodic memory based on content similarity.

        Args:
            similarity_threshold: Threshold above which records are considered duplicates.

        Returns:
            Number of records removed (merged).
        """
        logger.info("[KnowledgeLibrarian] Starting deduplication...")
        removed_count = 0

        try:
            # Process semantic memory
            if hasattr(self.memory, 'semantic') and hasattr(self.memory.semantic, 'records'):
                removed_count += self._deduplicate_store(self.memory.semantic, similarity_threshold)

            # Process episodic memory
            if hasattr(self.memory, 'episodic') and hasattr(self.memory.episodic, 'records'):
                removed_count += self._deduplicate_store(self.memory.episodic, similarity_threshold)

            logger.info(f"[KnowledgeLibrarian] Deduplication complete. Removed {removed_count} records.")
            self._audit_log("deduplicate", "memory_stores", "COMPLETED", {"removed": removed_count})
            return removed_count

        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Deduplication failed: {e}", exc_info=True)
            self._audit_log("deduplicate", "memory_stores", "FAILED", {"error": str(e)})
            return 0

    def _deduplicate_store(self, store, threshold: float) -> int:
        """Helper to deduplicate records within a single store."""
        if not hasattr(store, 'records') or not store.records:
            return 0

        removed = 0
        records = store.records
        i = 0
        while i < len(records):
            j = i + 1
            while j < len(records):
                try:
                    # Simple similarity: if both have string content, compare
                    rec_i = records[i]
                    rec_j = records[j]
                    if isinstance(rec_i.content, str) and isinstance(rec_j.content, str):
                        # Very naive similarity: if strings are identical, merge
                        if rec_i.content == rec_j.content:
                            # Merge tags and importance (max)
                            if hasattr(rec_i, 'tags') and hasattr(rec_j, 'tags'):
                                rec_i.tags = list(set(rec_i.tags + rec_j.tags))
                            rec_i.importance = max(rec_i.importance, rec_j.importance)
                            rec_i.usage_count += rec_j.usage_count
                            # Remove duplicate
                            records.pop(j)
                            removed += 1
                            continue  # don't increment j
                except Exception as e:
                    logger.warning(f"[KnowledgeLibrarian] Error during deduplication: {e}")
                j += 1
            i += 1

        logger.debug(f"[KnowledgeLibrarian] Deduplicated store: removed {removed} records.")
        return removed

    # ---------- Statistics ----------
    def get_stats(self) -> Dict[str, Any]:
        """
        Return statistics about the memory stores.

        Returns:
            Dict with counts of records in episodic and semantic stores.
        """
        try:
            episodic_count = 0
            semantic_count = 0

            if hasattr(self.memory, 'episodic') and hasattr(self.memory.episodic, 'records'):
                episodic_count = len(self.memory.episodic.records)

            if hasattr(self.memory, 'semantic') and hasattr(self.memory.semantic, 'records'):
                semantic_count = len(self.memory.semantic.records)

            return {
                "episodic_records": episodic_count,
                "semantic_records": semantic_count,
                "total_records": episodic_count + semantic_count,
            }
        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Failed to get stats: {e}", exc_info=True)
            return {"episodic_records": 0, "semantic_records": 0, "total_records": 0}

    # ---------- Shutdown ----------
    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("[KnowledgeLibrarian] Shutting down.")
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[KnowledgeLibrarian] Error closing secure memory: {e}")
        self._secure_memory = None
        self._secure_runner = None
