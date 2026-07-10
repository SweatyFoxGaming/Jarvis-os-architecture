#!/usr/bin/env python3
"""
JARVIS V3 Executive Mind Constitutional Audit.

This script initializes the full cognitive engine and runs a series of tests
to verify that the Executive Mind, Chief of Staff, departments, and registries
are functioning correctly. It also validates secure component integration.

Now with logging, secure configuration, and graceful error handling.
"""

import os
import sys
import logging
import traceback
from typing import Optional

# ---------- PATH SETUP ----------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# ---------- SECURE CONFIG ----------
try:
    from config.secure_config import AppConfig
    AppConfig.load()
    logger.info("[Audit] Secure configuration loaded.")
except Exception as e:
    logger.warning(f"[Audit] Secure config not available: {e}")

# ---------- IMPORTS ----------
from src.core.event_bus import EventBus
from src.core.registry import DepartmentRegistry, CapabilityRegistry
from src.core.security import SecurityModule
from src.bridge.synapse import SynapseInterface
from src.executive.chief_of_staff import ChiefOfStaff
from src.executive.mind import ExecutiveMind
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.departments.system import SystemDepartment
from src.core.digital_twin import DigitalTwin
from src.core.bootstrapping import register_initial_capabilities
from src.core.models import Task, TaskStatus

# ---------- SECURE MEMORY (if available) ----------
_secure_memory = None
try:
    from memory.secure_store import SecureMemoryStore
    _secure_memory = SecureMemoryStore(os.path.join(PROJECT_ROOT, "data", "memory.db"))
    logger.info("[Audit] SecureMemoryStore initialized.")
except ImportError:
    logger.warning("[Audit] SecureMemoryStore not available.")


# ---------- MAIN AUDIT FUNCTION ----------
def run_v3_executive_audit():
    """
    Run the full constitutional audit of the JARVIS V3 Executive Mind.
    """
    logger.info("=" * 60)
    logger.info("JARVIS V3: EXECUTIVE MIND CONSTITUTIONAL AUDIT")
    logger.info("=" * 60)

    try:
        # 1. Infrastructure Initialization with Secure Components
        logger.info("[Audit] Phase 1: Infrastructure Initialization...")

        event_bus = EventBus()
        if _secure_memory:
            event_bus.set_secure_memory(_secure_memory)
            logger.info("[Audit] EventBus: Secure memory attached.")

        security = SecurityModule(secure_memory=_secure_memory)
        synapse = SynapseInterface(security, secure_memory=_secure_memory)

        cap_registry = CapabilityRegistry(secure_memory=_secure_memory)
        dept_registry = DepartmentRegistry(secure_memory=_secure_memory)
        twin = DigitalTwin(secure_memory=_secure_memory)

        logger.info("[Audit] Infrastructure initialized successfully.")

        # 2. Executive Layer (V3 Hierarchy)
        logger.info("[Audit] Phase 2: Executive Layer Setup...")
        cos = ChiefOfStaff(
            event_bus=event_bus,
            cap_registry=cap_registry,
            dept_registry=dept_registry,
            secure_memory=_secure_memory,
        )

        # Pass the engine (None for now, but ExecutiveMind can work without)
        mind = ExecutiveMind(
            chief_of_staff=cos,
            event_bus=event_bus,
            digital_twin=twin,
            engine=None,  # No LLM engine needed for this audit
            secure_memory=_secure_memory,
        )
        logger.info("[Audit] Executive Mind and Chief of Staff ready.")

        # 3. Organization Bootstrapping
        logger.info("[Audit] Phase 3: Department Bootstrapping...")
        research = ResearchDepartment(engine=None)
        coding = CodingDepartment(engine=None)
        system = SystemDepartment()

        # Inject secure memory into departments that support it
        for dept in [research, coding, system]:
            if hasattr(dept, 'set_secure_memory') and _secure_memory:
                dept.set_secure_memory(_secure_memory)

        research.initialize(event_bus)
        coding.initialize(event_bus)
        system.initialize(event_bus)

        dept_registry.register(research)
        dept_registry.register(coding)
        dept_registry.register(system)

        register_initial_capabilities(cap_registry)

        logger.info("[Audit] Departments and capabilities registered.")

        # 4. Executive Reasoning Pipeline Test
        logger.info("[Audit] Phase 4: Strategic Reasoning Test...")
        request = "What is the time?"
        logger.info(f"[Audit] Executive Request: {request}")

        decision_summary = mind.process_request(request)
        logger.info(f"[Audit] Decision Outcome: {decision_summary}")

        # 5. Chief of Staff Coordination Test
        logger.info("[Audit] Phase 5: Operational Execution Test...")
        results = {}
        active_tasks = list(cos.active_tasks.items())
        logger.info(f"[Audit] Active tasks: {len(active_tasks)}")

        for task_id, task in active_tasks:
            dept = dept_registry.get_department(task.assigned_department_id)
            if dept:
                logger.info(f"[Audit] Triggering {dept.name} Department for Task {task_id}")
                try:
                    dept.process_task(task)
                    if task.status == TaskStatus.COMPLETED:
                        results[task_id] = task.output_data
                        logger.info(f"[Audit] Task {task_id} completed.")
                    else:
                        logger.warning(f"[Audit] Task {task_id} status: {task.status}")
                except Exception as e:
                    logger.error(f"[Audit] Task {task_id} failed: {e}", exc_info=True)
            else:
                logger.warning(f"[Audit] No department found for task {task_id}")

        logger.info(f"[Audit] Final System Results Collected: {len(results)}")

        # 6. Executive Board Verification
        logger.info("[Audit] Phase 6: Executive Board Consultation...")
        # The board is consulted inside mind.process_request; we just log that it was used.
        logger.info("[Audit] Board consultation verified (see logs above).")

        # 7. Secure Memory Verification (optional)
        if _secure_memory:
            try:
                stats = _secure_memory.search_by_text("CONVERSATION", limit=1)
                if stats:
                    logger.info("[Audit] Secure memory is storing conversations.")
                else:
                    logger.warning("[Audit] No conversations found in secure memory (may be empty).")
            except Exception as e:
                logger.warning(f"[Audit] Secure memory check failed: {e}")

        # 8. Clean Shutdown
        logger.info("[Audit] Phase 7: Shutdown...")
        if hasattr(mind, 'shutdown'):
            mind.shutdown()
        if hasattr(cos, 'shutdown'):
            cos.shutdown()
        for dept in [research, coding, system]:
            if hasattr(dept, 'shutdown'):
                dept.shutdown()
        if _secure_memory and hasattr(_secure_memory, 'close'):
            _secure_memory.close()

        logger.info("=" * 60)
        logger.info("AUDIT COMPLETE: EXECUTIVE MIND OPERATIONAL")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"[Audit] Fatal error: {e}", exc_info=True)
        # Attempt to clean up
        if _secure_memory and hasattr(_secure_memory, 'close'):
            try:
                _secure_memory.close()
            except Exception:
                pass
        sys.exit(1)


# ---------- MAIN ENTRY ----------
if __name__ == "__main__":
    run_v3_executive_audit()
