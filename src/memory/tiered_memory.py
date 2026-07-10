"""
Tiered Memory System for the Phoenix Intelligence Platform.

Provides three memory tiers:
- Working: Short-term, high‑importance context
- Episodic: Medium‑term, experience‑based
- Semantic: Long‑term, consolidated knowledge

Now with logging, error handling, audit logging, and memory pruning.
"""

import logging
from typing import List, Optional, Any, Dict
from datetime import datetime

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

# Logger
logger = logging.getLogger(__name__)


class MemoryTier:
    """
    A single tier of memory (Working, Episodic, Semantic).

    Stores records and provides retrieval methods.
    Now with logging and error handling.
    """

    def __init__(self, name: str, max_size: int = 1000):
        """
        Initialize a memory tier.

        Args:
            name: The name of the tier (e.g., "Working").
            max_size: Maximum number of records before pruning.
        """
        self.name = name
        self.records: List[MemoryRecord] = []
        self.max_size = max_size
        self._secure_memory: Optional[SecureMemoryStore] = None
        logger.info(f"[MemoryTier:{name}] Initialized with max_size={max_size}")

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info(f"[MemoryTier:{self.name}] SecureMemoryStore attached.")

    # ---------- Core Operations ----------
    def store(self, record: MemoryRecord) -> bool:
        """
        Store a memory record in this tier.

        Args:
            record: The MemoryRecord to store.

        Returns:
            True if stored, False if failed.
        """
        if record is None:
            logger.warning(f"[MemoryTier:{self.name}] store called with None record.")
            return False

        try:
            self.records.append(record)
            logger.debug(f"[MemoryTier:{self.name}] Stored record {record.uuid}")

            # Audit log to secure memory if available
            self._audit_log("store", str(record.uuid), "SUCCESS", {
                "source": record.source,
                "importance": record.importance,
                "tags": record.tags,
            })

            # Prune if over limit
            if len(self.records) > self.max_size:
                self._prune()

            return True

        except Exception as e:
            logger.error(f"[MemoryTier:{self.name}] Failed to store record: {e}", exc_info=True)
            self._audit_log("store", "unknown", "FAILED", {"error": str(e)})
            return False

    def retrieve(self, query: str, limit: int = 5) -> List[MemoryRecord]:
        """
        Retrieve records that contain the query string (case‑insensitive).

        Args:
            query: The search string.
            limit: Maximum number of records to return.

        Returns:
            List of matching MemoryRecord objects (most recent first).
        """
        if not query or not isinstance(query, str):
            logger.warning(f"[MemoryTier:{self.name}] retrieve called with invalid query.")
            return []

        try:
            if not self.records:
                return []

            query_lower = query.lower()
            results = []
            for record in reversed(self.records):  # newest first
                try:
                    # Convert content to string for searching
                    content_str = str(record.content).lower()
                    if query_lower in content_str:
                        results.append(record)
                        if len(results) >= limit:
                            break
                except Exception as e:
                    logger.warning(f"[MemoryTier:{self.name}] Error processing record {record.uuid}: {e}")
                    continue

            logger.debug(f"[MemoryTier:{self.name}] Retrieved {len(results)} records for query '{query[:30]}...'")
            return results

        except Exception as e:
            logger.error(f"[MemoryTier:{self.name}] Retrieval failed: {e}", exc_info=True)
            return []

    def get_recent(self, limit: int = 10) -> List[MemoryRecord]:
        """
        Return the most recent records.

        Args:
            limit: Maximum number of records.

        Returns:
            List of records (most recent first).
        """
        if limit <= 0:
            return []
        return list(reversed(self.records[-limit:]))

    def clear(self) -> bool:
        """
        Clear all records from this tier.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.records.clear()
            logger.info(f"[MemoryTier:{self.name}] Memory tier cleared.")
            self._audit_log("clear", self.name, "SUCCESS", {})
            return True
        except Exception as e:
            logger.error(f"[MemoryTier:{self.name}] Failed to clear: {e}", exc_info=True)
            return False

    def _prune(self) -> None:
        """
        Remove the oldest records to stay within max_size.
        """
        if len(self.records) <= self.max_size:
            return

        # Remove oldest (lowest priority/importance) - simple: remove from front
        # More sophisticated: sort by importance and recency
        # We'll remove the oldest 10% or at least one.
        to_remove = max(1, len(self.records) - self.max_size)
        # Sort by timestamp (oldest first) and remove oldest
        # Not exactly efficient for large lists, but acceptable.
        sorted_records = sorted(self.records, key=lambda r: r.timestamp)
        removed = sorted_records[:to_remove]
        self.records = sorted_records[to_remove:]
        logger.info(f"[MemoryTier:{self.name}] Pruned {len(removed)} old records.")

    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Internal audit logging."""
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"MEMORY_TIER:{self.name} - {action} on {resource} - {status}",
                    metadata={
                        "type": "memory_tier_audit",
                        "tier": self.name,
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details or {},
                    },
                )
            except Exception as e:
                logger.warning(f"[MemoryTier:{self.name}] Failed to audit log: {e}")


class HierarchicalMemory:
    """
    Three‑tier memory system: Working, Episodic, Semantic.

    Provides storage, retrieval, and consolidation utilities.
    Now with logging, error handling, and full integration.
    """

    def __init__(self, secure_memory: Optional[SecureMemoryStore] = None):
        """
        Initialize the hierarchical memory with three tiers.

        Args:
            secure_memory: Optional SecureMemoryStore for audit logging.
        """
        self.working = MemoryTier("Working", max_size=50)
        self.episodic = MemoryTier("Episodic", max_size=500)
        self.semantic = MemoryTier("Semantic", max_size=2000)

        # Attach secure memory to all tiers
        if secure_memory:
            self.set_secure_memory(secure_memory)

        logger.info(
            f"[HierarchicalMemory] Initialized. "
            f"SecureMemory: {secure_memory is not None}"
        )

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self.working.set_secure_memory(secure_memory)
        self.episodic.set_secure_memory(secure_memory)
        self.semantic.set_secure_memory(secure_memory)
        logger.info("[HierarchicalMemory] SecureMemoryStore attached to all tiers.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        # Not used directly, but keep for consistency.
        logger.info("[HierarchicalMemory] SecureCommandRunner attached (not used).")

    # ---------- Conversation Management ----------
    def store_conversation(self, user_input: str, response: str) -> bool:
        """
        Store a conversation turn in episodic memory.

        Args:
            user_input: The user's message.
            response: The assistant's response.

        Returns:
            True if stored, False otherwise.
        """
        if not user_input or not response:
            logger.warning("[HierarchicalMemory] store_conversation called with empty input or response.")
            return False

        try:
            record = MemoryRecord(
                source="conversation",
                content={"user": user_input, "jarvis": response},
                importance=0.7,
                tags=["conversation"],
                timestamp=datetime.now(),
            )
            return self.episodic.store(record)
        except Exception as e:
            logger.error(f"[HierarchicalMemory] Failed to store conversation: {e}", exc_info=True)
            return False

    def get_recent_context(self, limit: int = 3) -> str:
        """
        Retrieve the most recent conversation turns as a formatted string.

        Args:
            limit: Number of recent turns to include.

        Returns:
            Formatted context string.
        """
        try:
            recent = self.episodic.get_recent(limit)
            if not recent:
                return ""

            context_lines = ["Recent conversation:"]
            for r in recent:
                try:
                    content = r.content
                    if isinstance(content, dict):
                        user = content.get("user", "")
                        jarvis = content.get("jarvis", "")
                        context_lines.append(f"User: {user}")
                        context_lines.append(f"JARVIS: {jarvis}")
                        context_lines.append("")
                    else:
                        # If not a dict, fall back to string representation
                        context_lines.append(str(content))
                        context_lines.append("")
                except Exception as e:
                    logger.warning(f"[HierarchicalMemory] Error formatting record {r.uuid}: {e}")
                    continue

            return "\n".join(context_lines).strip()
        except Exception as e:
            logger.error(f"[HierarchicalMemory] Failed to get recent context: {e}", exc_info=True)
            return ""

    # ---------- General Retrieval ----------
    def search(self, query: str, tier: Optional[str] = None, limit: int = 5) -> Dict[str, List[MemoryRecord]]:
        """
        Search across one or all tiers.

        Args:
            query: The search string.
            tier: Optional specific tier name ("working", "episodic", "semantic").
            limit: Max results per tier.

        Returns:
            Dict mapping tier name to list of records.
        """
        if not query:
            return {}

        try:
            results = {}
            if tier is None or tier == "working":
                results["working"] = self.working.retrieve(query, limit)
            if tier is None or tier == "episodic":
                results["episodic"] = self.episodic.retrieve(query, limit)
            if tier is None or tier == "semantic":
                results["semantic"] = self.semantic.retrieve(query, limit)

            total = sum(len(v) for v in results.values())
            logger.debug(f"[HierarchicalMemory] Search '{query[:30]}...' found {total} records.")
            return results
        except Exception as e:
            logger.error(f"[HierarchicalMemory] Search failed: {e}", exc_info=True)
            return {}

    # ---------- Statistics ----------
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Return counts and sizes for each tier.

        Returns:
            Dict with tier name as key, and {'count': int, 'max_size': int}.
        """
        try:
            return {
                "working": {"count": len(self.working.records), "max_size": self.working.max_size},
                "episodic": {"count": len(self.episodic.records), "max_size": self.episodic.max_size},
                "semantic": {"count": len(self.semantic.records), "max_size": self.semantic.max_size},
            }
        except Exception as e:
            logger.error(f"[HierarchicalMemory] Failed to get stats: {e}", exc_info=True)
            return {}

    # ---------- Clear ----------
    def clear_all(self) -> bool:
        """
        Clear all memory tiers.

        Returns:
            True if all cleared, False if any failed.
        """
        success = True
        success &= self.working.clear()
        success &= self.episodic.clear()
        success &= self.semantic.clear()
        if success:
            logger.info("[HierarchicalMemory] All memory tiers cleared.")
        else:
            logger.warning("[HierarchicalMemory] Some tiers failed to clear.")
        return success

    # ---------- Shutdown ----------
    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("[HierarchicalMemory] Shutting down.")
        # Close any secure memory connections if needed.
        for tier in [self.working, self.episodic, self.semantic]:
            if hasattr(tier, '_secure_memory') and tier._secure_memory:
                if hasattr(tier._secure_memory, 'close'):
                    try:
                        tier._secure_memory.close()
                    except Exception as e:
                        logger.warning(f"[HierarchicalMemory] Error closing secure memory: {e}")
                tier._secure_memory = None
