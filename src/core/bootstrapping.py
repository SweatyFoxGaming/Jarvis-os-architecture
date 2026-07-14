"""
Bootstrapping module for registering initial capabilities.
"""

import logging
from typing import Optional

from src.core.tools import CapabilityRegistry, CapabilityDefinition, CapabilityParameter

try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

logger = logging.getLogger(__name__)

_secure_memory: Optional[SecureMemoryStore] = None
_secure_runner: Optional[SecureCommandRunner] = None


def set_secure_memory(secure_memory: SecureMemoryStore) -> None:
    global _secure_memory
    _secure_memory = secure_memory
    logger.info("[Bootstrapping] SecureMemoryStore attached.")


def set_secure_runner(secure_runner: SecureCommandRunner) -> None:
    global _secure_runner
    _secure_runner = secure_runner
    logger.info("[Bootstrapping] SecureCommandRunner attached.")


def _audit_log(action: str, resource: str, status: str, details: Optional[dict] = None) -> None:
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
    if cap_registry is None:
        raise ValueError("cap_registry cannot be None")

    logger.info("[Bootstrapping] Registering initial capabilities...")

    capabilities = [
        {
            "name": "research_specialist",
            "description": "Perform deep factual research and evidence collection.",
            "department": "Research",
        },
        {
            "name": "coding_specialist",
            "description": "Generate, analyze, and optimize source code.",
            "department": "Coding",
        },
        {
            "name": "time_service",
            "description": "Retrieve the current system time and date.",
            "department": "System",
        },
        {
            "name": "system_info",
            "description": "Retrieve hardware statistics and OS status.",
            "department": "System",
        },
    ]

    for entry in capabilities:
        cap_def = CapabilityDefinition(
            name=entry["name"],
            description=entry["description"],
            parameters=[],
            department=entry["department"],
        )
        try:
            cap_registry.register(cap_def)
            logger.info(f"[Bootstrapping] Registered capability '{cap_def.name}' → '{entry['department']}'")
            _audit_log("register_capability", cap_def.name, "SUCCESS", {"department": entry["department"]})
        except Exception as e:
            logger.error(f"[Bootstrapping] Failed to register capability '{cap_def.name}': {e}", exc_info=True)
            _audit_log("register_capability", cap_def.name, "FAILED", {"error": str(e)})
            raise

    logger.info("[Bootstrapping] Initial capabilities registered successfully.")
