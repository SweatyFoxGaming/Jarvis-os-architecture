"""
Digital Twin – A continuously evolving representation of reality.

Provides a central state store for JARVIS to reason about the world,
including hardware, projects, capabilities, and user identity.

Now with logging, audit logging, and error handling.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

# Logger
logger = logging.getLogger(__name__)


class DigitalTwinState(BaseModel):
    """
    Represents the entire state of the Digital Twin.
    """
    user_identity: Dict[str, Any] = Field(default_factory=dict)
    active_projects: List[str] = Field(default_factory=list)
    current_goals: List[str] = Field(default_factory=list)
    hardware_status: Dict[str, Any] = Field(default_factory=dict)
    software_environment: Dict[str, Any] = Field(default_factory=dict)
    available_capabilities: List[str] = Field(default_factory=list)
    running_tasks_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "forbid"


class DigitalTwin:
    """
    A continuously evolving internal representation of reality.
    Allows JARVIS to reason about the world rather than repeatedly rediscover it.

    Now with logging, audit logging, and exception handling.
    """

    def __init__(self, secure_memory: Optional[SecureMemoryStore] = None):
        """
        Initialize the Digital Twin with an empty state.

        Args:
            secure_memory: Optional SecureMemoryStore for audit logging.
        """
        self.state = DigitalTwinState()
        self._secure_memory = secure_memory
        self._secure_runner = None
        logger.info("[DigitalTwin] Initialized.")

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info("[DigitalTwin] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        self._secure_runner = secure_runner
        logger.info("[DigitalTwin] SecureCommandRunner attached.")

    # ---------- State Update Methods ----------
    def update_hardware(self, info: Dict[str, Any]) -> None:
        """
        Update hardware status and log the change.
        """
        if not isinstance(info, dict):
            logger.warning("[DigitalTwin] update_hardware called with non-dict input.")
            return

        self.state.hardware_status = info
        self.state.last_updated = datetime.now()
        logger.info(f"[DigitalTwin] Hardware status updated: {info.get('cpu_count', '?')} cores, {info.get('ram_total_gb', '?')} GB RAM")
        self._audit_log("update_hardware", "hardware_status", "SUCCESS", info)

    def update_capabilities(self, capabilities: List[str]) -> None:
        """
        Update the list of available capabilities.
        """
        if not isinstance(capabilities, list):
            logger.warning("[DigitalTwin] update_capabilities called with non-list input.")
            return

        self.state.available_capabilities = capabilities
        self.state.last_updated = datetime.now()
        logger.info(f"[DigitalTwin] Capabilities updated: {len(capabilities)} active")
        self._audit_log("update_capabilities", "available_capabilities", "SUCCESS", {"count": len(capabilities)})

    def add_project(self, project_name: str) -> bool:
        """
        Add a new project to the active list if not already present.

        Returns:
            True if added, False if already existed.
        """
        if not project_name or not isinstance(project_name, str):
            logger.warning("[DigitalTwin] add_project called with invalid project name.")
            return False

        if project_name in self.state.active_projects:
            logger.debug(f"[DigitalTwin] Project '{project_name}' already active.")
            return False

        self.state.active_projects.append(project_name)
        self.state.last_updated = datetime.now()
        logger.info(f"[DigitalTwin] Project added: {project_name}")
        self._audit_log("add_project", project_name, "SUCCESS", {})
        return True

    def remove_project(self, project_name: str) -> bool:
        """
        Remove a project from the active list.

        Returns:
            True if removed, False if not found.
        """
        if not project_name:
            return False

        try:
            self.state.active_projects.remove(project_name)
            self.state.last_updated = datetime.now()
            logger.info(f"[DigitalTwin] Project removed: {project_name}")
            self._audit_log("remove_project", project_name, "SUCCESS", {})
            return True
        except ValueError:
            logger.debug(f"[DigitalTwin] Project '{project_name}' not found for removal.")
            return False

    def set_user(self, user_info: Dict[str, Any]) -> None:
        """
        Update user identity information.
        """
        if not isinstance(user_info, dict):
            logger.warning("[DigitalTwin] set_user called with non-dict input.")
            return

        self.state.user_identity = user_info
        self.state.last_updated = datetime.now()
        logger.info(f"[DigitalTwin] User identity updated: {user_info.get('name', 'Unknown')}")
        self._audit_log("set_user", "user_identity", "SUCCESS", user_info)

    def update_environment(self, env_info: Dict[str, Any]) -> None:
        """
        Update software environment details (OS, version, etc.).
        """
        if not isinstance(env_info, dict):
            logger.warning("[DigitalTwin] update_environment called with non-dict input.")
            return

        self.state.software_environment = env_info
        self.state.last_updated = datetime.now()
        logger.info(f"[DigitalTwin] Software environment updated: {env_info.get('os', 'Unknown')}")
        self._audit_log("update_environment", "software_environment", "SUCCESS", env_info)

    def set_running_tasks_count(self, count: int) -> None:
        """
        Update the number of running tasks.
        """
        if not isinstance(count, int) or count < 0:
            logger.warning(f"[DigitalTwin] Invalid task count: {count}")
            return

        self.state.running_tasks_count = count
        self.state.last_updated = datetime.now()
        logger.debug(f"[DigitalTwin] Running tasks count: {count}")

    # ---------- State Access ----------
    def get_state(self) -> DigitalTwinState:
        """
        Return a copy of the current state.
        """
        return self.state.copy()

    def get_summary(self) -> str:
        """
        Return a human-readable summary of the current state.
        """
        os_info = self.state.software_environment.get('os', 'Unknown')
        projects = ', '.join(self.state.active_projects) if self.state.active_projects else 'None'
        capabilities_count = len(self.state.available_capabilities)

        return (
            f"Environment: {os_info}\n"
            f"Active Projects: {projects}\n"
            f"Capabilities: {capabilities_count} active\n"
            f"Running Tasks: {self.state.running_tasks_count}\n"
            f"Last Updated: {self.state.last_updated.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return the state as a dictionary (for serialization).
        """
        return self.state.dict()

    # ---------- Audit Logging ----------
    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Internal audit logging to secure memory."""
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"DIGITAL_TWIN: {action} on {resource} - {status}",
                    metadata={
                        "type": "digital_twin_audit",
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details or {},
                    },
                )
            except Exception as e:
                logger.warning(f"[DigitalTwin] Failed to audit log: {e}")

    # ---------- Shutdown ----------
    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("[DigitalTwin] Shutting down.")
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[DigitalTwin] Error closing secure memory: {e}")
        self._secure_memory = None
        self._secure_runner = None
