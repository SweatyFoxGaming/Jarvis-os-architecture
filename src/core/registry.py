import logging
from typing import Dict, Any, List, Optional, Tuple

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.core.interfaces import IDepartment
from src.core.models import Capability

# Logger
logger = logging.getLogger(__name__)


class DepartmentRegistry:
    """
    Registry for departments.
    Provides registration, retrieval, and listing of departments.
    Now with logging, error handling, and optional audit logging.
    """

    def __init__(
        self,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        self._departments: Dict[str, IDepartment] = {}
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner
        logger.info(f"[DepartmentRegistry] Initialized. SecureMemory: {secure_memory is not None}")

    # ---------- Dependency Injection Setters ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        self._secure_memory = secure_memory
        logger.info("[DepartmentRegistry] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        self._secure_runner = secure_runner
        logger.info("[DepartmentRegistry] SecureCommandRunner attached.")

    # ---------- Core Methods ----------
    def register(self, department: IDepartment) -> None:
        """
        Register a department. Raises ValueError if department already exists.
        Stores audit entry in secure memory if available.
        """
        if not department or not hasattr(department, 'name'):
            raise ValueError("Invalid department object (missing 'name' attribute).")

        name = department.name
        if name in self._departments:
            logger.warning(f"[DepartmentRegistry] Department '{name}' already registered. Overwriting.")
            # Optionally, we could raise an error, but we'll allow overwrite with warning.

        self._departments[name] = department
        logger.info(f"[DepartmentRegistry] Registered department: {name}")

        # Audit log in secure memory
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"REGISTRY: Department '{name}' registered.",
                    metadata={"type": "registry_audit", "action": "register_department", "name": name}
                )
            except Exception as e:
                logger.warning(f"[DepartmentRegistry] Failed to audit register: {e}")

    def get_department(self, name: str) -> Optional[IDepartment]:
        """
        Retrieve a department by name. Returns None if not found.
        """
        if not name:
            logger.warning("[DepartmentRegistry] get_department called with empty name.")
            return None

        dept = self._departments.get(name)
        if dept is None:
            logger.debug(f"[DepartmentRegistry] Department '{name}' not found.")
        else:
            logger.debug(f"[DepartmentRegistry] Retrieved department '{name}'.")
        return dept

    def list_departments(self) -> List[str]:
        """Return a list of all registered department names."""
        return list(self._departments.keys())

    # ---------- Shutdown ----------
    def shutdown(self):
        """Clean up resources."""
        logger.info("[DepartmentRegistry] Shutting down.")
        self._departments.clear()
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[DepartmentRegistry] Error closing secure memory: {e}")


class CapabilityRegistry:
    """
    Registry for capabilities, mapping capability names to (Capability, department_name).
    Provides registration, metadata retrieval, and department lookup.
    Now with logging, error handling, and audit logging.
    """

    def __init__(
        self,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        # Maps capability names to (Capability, department_name)
        self._capabilities: Dict[str, Tuple[Capability, str]] = {}
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner
        logger.info(f"[CapabilityRegistry] Initialized. SecureMemory: {secure_memory is not None}")

    # ---------- Dependency Injection Setters ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        self._secure_memory = secure_memory
        logger.info("[CapabilityRegistry] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        self._secure_runner = secure_runner
        logger.info("[CapabilityRegistry] SecureCommandRunner attached.")

    # ---------- Core Methods ----------
    def register(self, capability: Capability, department_name: str) -> None:
        """
        Register a capability with its responsible department.
        Raises ValueError if capability already exists (optional, we warn and overwrite).
        Stores audit entry in secure memory if available.
        """
        if not capability or not hasattr(capability, 'name'):
            raise ValueError("Invalid capability object (missing 'name' attribute).")
        if not department_name:
            raise ValueError("department_name cannot be empty.")

        name = capability.name
        if name in self._capabilities:
            logger.warning(f"[CapabilityRegistry] Capability '{name}' already registered. Overwriting.")

        self._capabilities[name] = (capability, department_name)
        logger.info(f"[CapabilityRegistry] Registered capability '{name}' to department '{department_name}'.")

        # Audit log in secure memory
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"REGISTRY: Capability '{name}' -> '{department_name}'.",
                    metadata={
                        "type": "registry_audit",
                        "action": "register_capability",
                        "capability": name,
                        "department": department_name,
                    },
                )
            except Exception as e:
                logger.warning(f"[CapabilityRegistry] Failed to audit register: {e}")

    def get_metadata(self, capability_name: str) -> Optional[Capability]:
        """
        Retrieve the Capability object for a given capability name.
        Returns None if not found.
        """
        if not capability_name:
            logger.warning("[CapabilityRegistry] get_metadata called with empty name.")
            return None

        entry = self._capabilities.get(capability_name)
        if entry is None:
            logger.debug(f"[CapabilityRegistry] Capability '{capability_name}' not found.")
            return None
        return entry[0]  # Capability object

    def find_department(self, capability_name: str) -> Optional[str]:
        """
        Find the department responsible for a given capability.
        Returns None if not found.
        """
        if not capability_name:
            logger.warning("[CapabilityRegistry] find_department called with empty name.")
            return None

        entry = self._capabilities.get(capability_name)
        if entry is None:
            logger.debug(f"[CapabilityRegistry] Department for '{capability_name}' not found.")
            return None
        return entry[1]  # department name

    def list_capabilities(self) -> List[str]:
        """Return a list of all registered capability names."""
        return list(self._capabilities.keys())

    def get_all_mappings(self) -> Dict[str, Tuple[Capability, str]]:
        """
        Return a copy of the full capability→department mapping.
        Useful for diagnostics.
        """
        return self._capabilities.copy()

    # ---------- Shutdown ----------
    def shutdown(self):
        """Clean up resources."""
        logger.info("[CapabilityRegistry] Shutting down.")
        self._capabilities.clear()
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[CapabilityRegistry] Error closing secure memory: {e}")
