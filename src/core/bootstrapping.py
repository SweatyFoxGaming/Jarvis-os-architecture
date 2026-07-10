"""
Bootstrapping module for registering initial capabilities.

This module registers the core capabilities (research, coding, system)
into the CapabilityRegistry during system startup.
"""

import logging
from typing import Optional

from src.core.models import Capability
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.core.registry import CapabilityRegistry

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

# Global reference for secure memory (if needed for audit)
_secure_memory: Optional[SecureMemoryStore] = None
_secure_runner: Optional[SecureCommandRunner] = None


def set_secure_memory(secure_memory: SecureMemoryStore) -> None:
    """
    Inject secure memory for audit logging.
    """
    global _secure_memory
    _secure_memory = secure_memory
    logger.info("[Bootstrapping] SecureMemoryStore attached.")


def set_secure_runner(secure_runner: SecureCommandRunner) -> None:
    """
    Inject secure command runner (for future use).
    """
    global _secure_runner
    _secure_runner = secure_runner
    logger.info("[Bootstrapping] SecureCommandRunner attached.")


def _audit_log(action: str, resource: str, status: str, details: Optional[dict] = None) -> None:
    """Internal audit logging to secure memory."""
    if _secure_memory is not None:
        try:
            _secure_memory.insert(
                text=f"BOOTSTRAP: {action} on {resource} - {status}",
                metadata={
                    "type": "bootstrapping_audit",
                    "action": action,
                    "resource": resource,
                    "status": status,
                    "details": details or {},
                },
            )
        except Exception as e:
            logger.warning(f"[Bootstrapping] Failed to audit log: {e}")


def register_initial_capabilities(cap_registry: CapabilityRegistry) -> None:
    """
    Register the initial set of capabilities into the given CapabilityRegistry.

    Args:
        cap_registry: The CapabilityRegistry instance to register with.

    Raises:
        ValueError: If the registry is None.
    """
    if cap_registry is None:
        raise ValueError("cap_registry cannot be None")

    logger.info("[Bootstrapping] Registering initial capabilities...")

    # Define capabilities with their department names
    capabilities = [
        # Research
        {
            "capability": Capability(
                name="research_specialist",
                purpose="Perform deep factual research and evidence collection.",
                inputs={"objective": "The topic to research"},
                outputs={"report": "Factual summary with evidence"},
                estimated_time_sec=30,
            ),
            "department": "Research",
        },
        # Coding
        {
            "capability": Capability(
                name="coding_specialist",
                purpose="Generate, analyze, and optimize source code.",
                inputs={"objective": "Coding task description"},
                outputs={"code": "Source code", "language": "Programming language"},
                estimated_time_sec=45,
            ),
            "department": "Coding",
        },
        # System - Time
        {
            "capability": Capability(
                name="time_service",
                purpose="Retrieve the current system time and date.",
                estimated_time_sec=1,
            ),
            "department": "System",
        },
        # System - System Info
        {
            "capability": Capability(
                name="system_info",
                purpose="Retrieve hardware statistics and OS status.",
                estimated_time_sec=1,
            ),
            "department": "System",
        },
    ]

    # Register each capability with error handling
    for entry in capabilities:
        cap = entry["capability"]
        dept = entry["department"]
        try:
            cap_registry.register(cap, dept)
            logger.info(f"[Bootstrapping] Registered capability '{cap.name}' → '{dept}'")
            _audit_log("register_capability", cap.name, "SUCCESS", {"department": dept})
        except Exception as e:
            logger.error(f"[Bootstrapping] Failed to register capability '{cap.name}': {e}", exc_info=True)
            _audit_log("register_capability", cap.name, "FAILED", {"error": str(e)})
            # Re-raise if you want to halt startup, or swallow to continue.
            # We'll raise to make it obvious during development.
            raise

    logger.info("[Bootstrapping] Initial capabilities registered successfully.")
