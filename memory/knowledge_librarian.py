# memory/knowledge_librarian.py (reinforced with verification)
import logging
import traceback
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from src.core.models import MemoryRecord
from src.memory.tiered_memory import HierarchicalMemory

logger = logging.getLogger(__name__)

class KnowledgeLibrarian:
    """
    Manages consolidation of episodic memory into semantic memory.
    Now includes a verification pipeline to prevent hallucination loops.
    """

    def __init__(self, memory: HierarchicalMemory, secure_memory=None):
        self.memory = memory
        self._secure_memory = secure_memory
        self._pending_verification: List[MemoryRecord] = []
        self._verification_threshold = 0.9  # auto-promote only if importance > 0.9 AND verified

    # ---------- Core Consolidation ----------
    def consolidate_episodes(self, min_importance: float = 0.8) -> int:
        """
        Process episodic records:
        - Auto-promote records that are already verified AND have high importance.
        - Move unverified but important records to pending_verification.
        """
        logger.info("[KnowledgeLibrarian] Starting consolidation...")
        promoted_count = 0

        try:
            if not hasattr(self.memory, 'episodic') or not hasattr(self.memory.episodic, 'records'):
                logger.warning("[KnowledgeLibrarian] Episodic memory not available.")
                return 0

            records = self.memory.episodic.records[:]  # copy
            for record in records:
                try:
                    # Case 1: Already verified and high importance -> auto-promote
                    if record.verification_status == "verified" and record.importance >= self._verification_threshold:
                        self.memory.semantic.store(record)
                        promoted_count += 1
                        logger.debug(f"[KnowledgeLibrarian] Auto-promoted record {record.uuid}")
                        self._audit_log("auto_promote", str(record.uuid), "SUCCESS", {"importance": record.importance})
                        continue

                    # Case 2: Unverified but important -> move to pending
                    if record.verification_status == "unverified" and record.importance >= min_importance:
                        self._pending_verification.append(record)
                        record.verification_status = "pending_review"
                        logger.info(f"[KnowledgeLibrarian] Record {record.uuid} moved to pending verification.")
                        self._audit_log("pending_review", str(record.uuid), "PENDING", {"importance": record.importance})
                        continue

                    # Case 3: Low importance or already in semantic -> ignore
                except Exception as e:
                    logger.warning(f"[KnowledgeLibrarian] Error processing record {record.uuid}: {e}")

            logger.info(f"[KnowledgeLibrarian] Consolidation complete. Promoted {promoted_count} records.")
            return promoted_count

        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Consolidation failed: {e}", exc_info=True)
            return 0

    # ---------- Verification API ----------
    def get_pending_records(self) -> List[Dict[str, Any]]:
        """Return a list of records awaiting human verification."""
        return [
            {
                "uuid": str(r.uuid),
                "content": r.content,
                "source": r.source,
                "importance": r.importance,
                "timestamp": r.timestamp.isoformat(),
                "tags": r.tags,
            }
            for r in self._pending_verification
        ]

    def verify_record(self, record_uuid: str, approved: bool) -> bool:
        """
        Manually verify a pending record.
        Returns True if processed, False if not found.
        """
        target = None
        for r in self._pending_verification:
            if str(r.uuid) == record_uuid:
                target = r
                break

        if target is None:
            logger.warning(f"[KnowledgeLibrarian] Record {record_uuid} not found in pending.")
            return False

        try:
            if approved:
                target.verification_status = "human_verified"
                self.memory.semantic.store(target)
                self._pending_verification.remove(target)
                logger.info(f"[KnowledgeLibrarian] Record {record_uuid} approved by human.")
                self._audit_log("human_approve", record_uuid, "SUCCESS", {})
            else:
                target.verification_status = "rejected"
                self._pending_verification.remove(target)
                logger.info(f"[KnowledgeLibrarian] Record {record_uuid} rejected by human.")
                self._audit_log("human_reject", record_uuid, "REJECTED", {})
            return True
        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Failed to verify record {record_uuid}: {e}", exc_info=True)
            return False

    def verify_all_pending(self, approve: bool) -> int:
        """Bulk approve/reject all pending records."""
        count = 0
        for r in self._pending_verification[:]:
            if self.verify_record(str(r.uuid), approve):
                count += 1
        return count

    # ---------- Programmatic Validation (optional) ----------
    def validate_candidate(self, candidate: MemoryRecord, source_episodes: List[MemoryRecord]) -> bool:
        """
        Simple consistency check: compare candidate content with source episodes.
        Returns True if consistent (no contradictions).
        """
        # Simple heuristic: if candidate is a string and source episodes contain similar content?
        # For production, integrate with DeepEval or similar.
        # Placeholder: always return True, but log for monitoring.
        logger.debug(f"[KnowledgeLibrarian] Validating candidate {candidate.uuid}")
        # In a real implementation, you'd check factual consistency.
        return True

    # ---------- Internal Helpers ----------
    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None):
        if self._secure_memory:
            try:
                self._secure_memory.insert(
                    text=f"KNOWLEDGE_LIBRARIAN: {action} on {resource} - {status}",
                    metadata={"type": "librarian_audit", "action": action, "resource": resource, "status": status, "details": details or {}}
                )
            except Exception as e:
                logger.warning(f"[KnowledgeLibrarian] Audit log failed: {e}")

    # ---------- Shutdown ----------
    def shutdown(self):
        logger.info("[KnowledgeLibrarian] Shutting down.")
        self._pending_verification.clear()
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            self._secure_memory.close()
