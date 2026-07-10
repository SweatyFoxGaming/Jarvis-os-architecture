"""
Knowledge Librarian – Manages consolidation of episodic to semantic memory.
Now with programmatic validation to prevent hallucination loops.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from src.core.models import MemoryRecord
from src.memory.tiered_memory import HierarchicalMemory

logger = logging.getLogger(__name__)

# Read config from environment
VALIDATION_ENABLED = os.getenv("VALIDATION_ENABLED", "true").lower() in ("true", "1", "yes")
VALIDATION_CONFIDENCE_THRESHOLD = float(os.getenv("VALIDATION_CONFIDENCE_THRESHOLD", "0.7"))
VALIDATION_USE_LLM = os.getenv("VALIDATION_USE_LLM", "true").lower() in ("true", "1", "yes")


class KnowledgeLibrarian:
    def __init__(self, memory: HierarchicalMemory, secure_memory=None, engine=None):
        self.memory = memory
        self._secure_memory = secure_memory
        self._engine = engine
        self._pending_verification: List[MemoryRecord] = []
        self._verification_threshold = 0.9  # auto-promote only if importance > 0.9 AND verified
        logger.info("[KnowledgeLibrarian] Initialized.")

    def set_engine(self, engine):
        self._engine = engine
        logger.info("[KnowledgeLibrarian] LLM engine attached.")

    # ---------- Validation ----------
    def _validate_candidate(self, candidate: MemoryRecord) -> tuple[bool, float, str]:
        """
        Validate a candidate record using LLM‑based fact‑checking.
        Returns (is_consistent, confidence, reason).
        """
        if not VALIDATION_ENABLED:
            return True, 1.0, "Validation disabled."

        if not self._engine or not VALIDATION_USE_LLM:
            # Fallback: accept with a default confidence
            return True, 0.8, "Validation skipped (no engine)."

        # Retrieve relevant semantic records for context
        query_text = str(candidate.content)
        semantic_context = []
        if hasattr(self.memory, 'semantic') and hasattr(self.memory.semantic, 'records'):
            # Get recent semantic records for context
            for rec in self.memory.semantic.records[-10:]:
                if isinstance(rec.content, str):
                    semantic_context.append(rec.content)

        # Build prompt for validation
        prompt = f"""
You are a fact‑checking assistant. Your task is to determine if a new statement is consistent with existing knowledge.

Existing knowledge:
{chr(10).join(semantic_context) if semantic_context else "No existing knowledge."}

New statement: {query_text}

Answer with JSON only:
{{
  "consistent": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}}
"""
        try:
            response = self._engine.generate(prompt, max_tokens=256, temperature=0.2)
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                consistent = data.get("consistent", True)
                confidence = data.get("confidence", 0.5)
                reason = data.get("reason", "No reason provided.")
                logger.debug(f"[KnowledgeLibrarian] Validation result: consistent={consistent}, confidence={confidence}")
                return consistent, confidence, reason
            else:
                logger.warning(f"[KnowledgeLibrarian] Could not parse validation response: {response[:200]}")
                return True, 0.5, "Could not parse validation."
        except Exception as e:
            logger.warning(f"[KnowledgeLibrarian] Validation error: {e}")
            return True, 0.5, f"Validation error: {e}"

    # ---------- Consolidation ----------
    def consolidate_episodes(self, min_importance: float = 0.8) -> int:
        promoted = 0
        try:
            if not hasattr(self.memory, 'episodic') or not hasattr(self.memory.episodic, 'records'):
                return 0

            records = self.memory.episodic.records[:]
            for record in records:
                # Already verified and high importance → auto‑promote
                if record.verification_status == "verified" and record.importance >= self._verification_threshold:
                    self.memory.semantic.store(record)
                    promoted += 1
                    logger.debug(f"[KnowledgeLibrarian] Auto‑promoted record {record.uuid}")
                    continue

                # Unverified but important → validate
                if record.verification_status == "unverified" and record.importance >= min_importance:
                    # Run validation
                    is_consistent, confidence, reason = self._validate_candidate(record)
                    if is_consistent and confidence >= VALIDATION_CONFIDENCE_THRESHOLD:
                        record.verification_status = "verified_by_llm"
                        self.memory.semantic.store(record)
                        promoted += 1
                        logger.info(f"[KnowledgeLibrarian] Validated and promoted record {record.uuid} (conf={confidence:.2f})")
                    else:
                        # Move to pending for human review
                        record.verification_status = "pending_review"
                        self._pending_verification.append(record)
                        logger.info(f"[KnowledgeLibrarian] Record {record.uuid} moved to pending (reason: {reason})")

            logger.info(f"[KnowledgeLibrarian] Consolidation complete. Promoted {promoted} records.")
            return promoted
        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Consolidation failed: {e}", exc_info=True)
            return 0

    # ---------- Human Verification ----------
    def get_pending_records(self) -> List[Dict[str, Any]]:
        return [
            {
                "uuid": str(r.uuid),
                "content": r.content,
                "source": r.source,
                "importance": r.importance,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "tags": r.tags,
            }
            for r in self._pending_verification
        ]

    def verify_record(self, record_uuid: str, approved: bool) -> bool:
        target = None
        for r in self._pending_verification:
            if str(r.uuid) == record_uuid:
                target = r
                break
        if target is None:
            return False
        try:
            if approved:
                target.verification_status = "human_verified"
                self.memory.semantic.store(target)
                logger.info(f"[KnowledgeLibrarian] Record {record_uuid} approved by human.")
            else:
                target.verification_status = "rejected"
                logger.info(f"[KnowledgeLibrarian] Record {record_uuid} rejected.")
            self._pending_verification.remove(target)
            return True
        except Exception as e:
            logger.error(f"[KnowledgeLibrarian] Verification failed: {e}")
            return False

    def verify_all_pending(self, approve: bool) -> int:
        count = 0
        for r in self._pending_verification[:]:
            if self.verify_record(str(r.uuid), approve):
                count += 1
        return count

    def shutdown(self):
        logger.info("[KnowledgeLibrarian] Shutting down.")
        self._pending_verification.clear()
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception:
                pass
