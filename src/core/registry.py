"""
Core Registry – DepartmentRegistry and thin wrapper for Capability Registry.
Maintained for backward compatibility.
"""

import logging
from typing import Optional, List, Dict, Any

# For DepartmentRegistry (unchanged)
from src.core.models import Capability
from src.core.interfaces import IDepartment, ICapabilityRegistry

# Import the actual capability registry from the Capability Platform
from src.capabilities import CapabilityRegistry as NewCapabilityRegistry
from src.capabilities.manifest import CapabilityManifest
from src.capabilities.contract import Capability as NewCapability

logger = logging.getLogger(__name__)


# ---------- DepartmentRegistry (unchanged) ----------
class DepartmentRegistry:
    """Registry for departments."""
    def __init__(self):
        self._departments: Dict[str, IDepartment] = {}
        self._secure_memory = None
        logger.info("[DepartmentRegistry] Initialized. SecureMemory: False")

    def set_secure_memory(self, secure_memory):
        self._secure_memory = secure_memory
        logger.info("[DepartmentRegistry] SecureMemoryStore attached.")

    def register(self, department: IDepartment) -> None:
        self._departments[department.name] = department
        logger.info(f"[DepartmentRegistry] Registered department: {department.name}")

    def get_department(self, name: str) -> Optional[IDepartment]:
        return self._departments.get(name)

    def list_departments(self) -> List[str]:
        return list(self._departments.keys())


# ---------- CapabilityRegistry (thin wrapper) ----------
class CapabilityRegistry(ICapabilityRegistry):
    """
    Thin wrapper around the Capability Platform registry.
    Maintains backward compatibility.
    """

    def __init__(self):
        self._registry = NewCapabilityRegistry()
        self._secure_memory = None
        logger.info("[CapabilityRegistry] Initialized (wrapper).")

    def set_secure_memory(self, secure_memory):
        self._secure_memory = secure_memory
        logger.info("[CapabilityRegistry] SecureMemoryStore attached.")

    def register(self, capability: Capability, department: str = "System") -> None:
        """Register a capability (legacy format)."""
        manifest = CapabilityManifest(
            identity={
                "id": capability.name,
                "name": capability.name,
                "description": capability.purpose,
            },
            classification={"category": "legacy", "tags": []},
            requirements={"permissions": [], "dependencies": []},
            execution={"entrypoint": "", "timeout": 60},
            resources={"estimated_tokens": 0, "estimated_memory_mb": 0, "estimated_duration_sec": 0},
            lifecycle={"version": "1.0.0"},
            metadata={"author": "Jarvis Core", "source": "legacy"}
        )
        self._registry._manifests[capability.name] = manifest
        self._registry._implementations[capability.name] = None
        logger.info(f"[CapabilityRegistry] Registered capability '{capability.name}' to department '{department}'.")

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return [m.model_dump(mode='json') for m in self._registry._manifests.values()]

    def get_capability(self, name: str) -> Optional[NewCapability]:
        return self._registry.get(name)

    def find_department(self, capability_name: str) -> Optional[str]:
        # Legacy mapping; in the new system, departments are not used for routing.
        return "System"


# ---------- Singleton accessor ----------
_registry_singleton = None

def get_capability_registry() -> CapabilityRegistry:
    """Return the singleton CapabilityRegistry instance."""
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = CapabilityRegistry()
        logger.info("[CoreRegistry] Created singleton CapabilityRegistry wrapper.")
    return _registry_singleton
