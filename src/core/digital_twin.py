"""
Digital Twin – A continuously evolving representation of reality.

Now stores its state as MemoryRecords in the secure memory store,
making it queryable, auditable, and persistent.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.core.models import MemoryRecord, MemoryStage

try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

logger = logging.getLogger(__name__)


class DigitalTwin:
    """
    Maintains a continuously evolving representation of the system state.
    All state changes are stored as MemoryRecords with stage="system_state".
    """

    def __init__(self, secure_memory: Optional[SecureMemoryStore] = None):
        self._secure_memory = secure_memory
        self._state_cache: Dict[str, Any] = {}   # in‑memory cache for fast access
        self._last_state_record_id: Optional[int] = None
        logger.info("[DigitalTwin] Initialized.")

    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        self._secure_memory = secure_memory
        logger.info("[DigitalTwin] SecureMemoryStore attached.")

    # ---------- Private helpers ----------
    def _store_state_snapshot(self, state_type: str, data: Dict[str, Any]) -> None:
        """Store a state snapshot as a MemoryRecord."""
        if not self._secure_memory:
            logger.debug("[DigitalTwin] No secure memory – skipping state storage.")
            return

        try:
            text = f"SYSTEM_STATE: {state_type} - {data}"
            metadata = {
                "type": "system_state",
                "state_type": state_type,
                "timestamp": datetime.now().isoformat(),
                **data,
            }
            record_id = self._secure_memory.insert(text, metadata, user_id="system")
            self._last_state_record_id = record_id
            logger.debug(f"[DigitalTwin] Stored {state_type} state snapshot (id={record_id})")
        except Exception as e:
            logger.warning(f"[DigitalTwin] Failed to store state snapshot: {e}")

    def _get_latest_state(self, state_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve the latest state snapshot of a given type from Memory."""
        if not self._secure_memory:
            return None
        try:
            # Search for the latest record with metadata.type == "system_state" and state_type == state_type
            results = self._secure_memory.search_by_text("SYSTEM_STATE", limit=10)
            for r in results:
                meta = r.get("metadata", {})
                if meta.get("type") == "system_state" and meta.get("state_type") == state_type:
                    return meta
            return None
        except Exception as e:
            logger.warning(f"[DigitalTwin] Failed to retrieve state: {e}")
            return None

    # ---------- Public API ----------
    def update_hardware(self, hardware_info: Dict[str, Any]) -> None:
        """Update hardware information and store it in Memory."""
        self._state_cache["hardware"] = hardware_info
        self._store_state_snapshot("hardware", hardware_info)
        logger.info(f"[DigitalTwin] Hardware status updated: {hardware_info.get('cpu_count', '?')} cores, {hardware_info.get('total_ram_gb', '?')} GB RAM")

    def update_capabilities(self, capabilities: List[str]) -> None:
        """Update the list of available capabilities and store in Memory."""
        self._state_cache["capabilities"] = capabilities
        self._store_state_snapshot("capabilities", {"count": len(capabilities), "list": capabilities})
        logger.info(f"[DigitalTwin] Capabilities updated: {len(capabilities)} active")

    def update_environment(self, env_info: Dict[str, Any]) -> None:
        """Update software environment details and store in Memory."""
        self._state_cache["environment"] = env_info
        self._store_state_snapshot("environment", env_info)
        logger.info(f"[DigitalTwin] Software environment updated: {env_info.get('os', 'Unknown')}")

    def get_hardware(self) -> Dict[str, Any]:
        """Return the latest hardware state (from cache or Memory)."""
        if "hardware" in self._state_cache:
            return self._state_cache["hardware"]
        result = self._get_latest_state("hardware")
        if result:
            self._state_cache["hardware"] = result
            return result
        return {}

    def get_capabilities(self) -> List[str]:
        """Return the latest capabilities list (from cache or Memory)."""
        if "capabilities" in self._state_cache:
            return self._state_cache["capabilities"]
        result = self._get_latest_state("capabilities")
        if result:
            self._state_cache["capabilities"] = result.get("list", [])
            return self._state_cache["capabilities"]
        return []

    def get_environment(self) -> Dict[str, Any]:
        """Return the latest environment state (from cache or Memory)."""
        if "environment" in self._state_cache:
            return self._state_cache["environment"]
        result = self._get_latest_state("environment")
        if result:
            self._state_cache["environment"] = result
            return result
        return {}

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        return {
            "hardware": self.get_hardware(),
            "capabilities": self.get_capabilities(),
            "environment": self.get_environment(),
        }

    def shutdown(self) -> None:
        logger.info("[DigitalTwin] Shutting down.")
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[DigitalTwin] Error closing secure memory: {e}")
        self._secure_memory = None
        self._state_cache.clear()
