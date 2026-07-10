import os
import sys
import logging

# ---------- 1. PATH SETUP ----------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------- 2. LOGGING (Inherits from main.py, but safe fallback) ----------
logger = logging.getLogger(__name__)

# ---------- 3. SECURE IMPORTS (Now used!) ----------
try:
    from config.secure_config import AppConfig
    # Force config load at engine startup (idempotent)
    AppConfig.load()
    logger.info("✅ Secure configuration validated.")
except ImportError:
    logger.warning("config.secure_config not found. Running without secure config.")
    AppConfig = None
except ValueError as e:
    logger.critical(f"❌ Config error: {e}. Ensure .env file exists.")
    raise  # Re-raise to stop startup

try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None
    logger.warning("SecureMemoryStore not available. Memory will be insecure or missing.")

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None
    logger.warning("SecureCommandRunner not available. Command execution will be unsafe.")

# ---------- 4. ORIGINAL IMPORTS (Your existing modules) ----------
from src.core.event_bus import EventBus
from src.core.registry import DepartmentRegistry, CapabilityRegistry
from src.core.hardware import HardwareManager
from src.core.model_manager import ModelManager
from src.executive.chief_of_staff import ChiefOfStaff
from src.executive.mind import ExecutiveMind
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.departments.system import SystemDepartment
from src.core.digital_twin import DigitalTwin
from src.core.bootstrapping import register_initial_capabilities

# Use our **fixed** LLMEngine (the one we rewrote earlier)
from src.llm_engine import LLMEngine


class CognitiveEngineV3:
    def __init__(self, 
                 secure_memory: SecureMemoryStore = None,
                 secure_runner: SecureCommandRunner = None):
        """
        Initialize the JARVIS V3 cognitive engine.
        Optionally inject secure components for enhanced security.
        """
        # ---------- 5. SECURE COMPONENTS ----------
        # If not injected, create them using defaults (if available)
        self.secure_memory = secure_memory or (
            SecureMemoryStore(os.path.join(PROJECT_ROOT, "data", "memory.db")) 
            if SecureMemoryStore else None
        )
        self.secure_runner = secure_runner or (SecureCommandRunner if SecureCommandRunner else None)

        if self.secure_memory:
            logger.info("✅ Secure Memory Store attached.")
        if self.secure_runner:
            logger.info("✅ Secure Command Runner attached.")

        # ---------- 6. INFRASTRUCTURE ----------
        self.event_bus = EventBus()
        self.dept_registry = DepartmentRegistry()
        self.cap_registry = CapabilityRegistry()
        self.twin = DigitalTwin()

        # Hardware detection (may use secure config if needed – we'll keep original)
        try:
            hardware_info = HardwareManager.detect_hardware()
            self.twin.update_hardware(hardware_info)
            settings = HardwareManager.get_optimized_settings(hardware_info)
        except Exception as e:
            logger.warning(f"Hardware detection failed: {e}. Using defaults.")
            settings = {"context_window": 2048, "n_ctx": 2048, "n_batch": 512}

        self.model_manager = ModelManager(settings)

        # ---------- 7. LLM ENGINE (Our fixed version) ----------
        self.engine = LLMEngine()  # This now properly loads and uses the model
        logger.info(f"✅ LLM Engine initialized. Real model loaded: {self.engine.llm is not None}")

        # ---------- 8. EXECUTIVE HIERARCHY ----------
        self.cos = ChiefOfStaff(self.event_bus, self.cap_registry, self.dept_registry)
        self.mind = ExecutiveMind(self.cos, self.event_bus, self.twin)

        # ---------- 9. DEPARTMENTS (Injected with secure components) ----------
        # Research & Coding need the engine; they can also use secure_memory if they accept it.
        # Since we don't know their signatures, we pass via keyword if they support it.
        self.research_dept = ResearchDepartment(self.engine)
        self.coding_dept = CodingDepartment(self.engine)
        self.system_dept = SystemDepartment()

        # Optionally attach secure components to departments if they have attributes
        for dept in [self.research_dept, self.coding_dept, self.system_dept]:
            if hasattr(dept, 'set_secure_memory') and self.secure_memory:
                dept.set_secure_memory(self.secure_memory)
            if hasattr(dept, 'set_secure_runner') and self.secure_runner:
                dept.set_secure_runner(self.secure_runner)

        # ---------- 10. INITIALIZATION ----------
        self._setup()

    def _setup(self):
        """Register departments and capabilities."""
        # Initialize departments (original logic)
        self.research_dept.initialize(self.event_bus)
        self.coding_dept.initialize(self.event_bus)
        self.system_dept.initialize(self.event_bus)

        # Register departments
        self.dept_registry.register(self.research_dept)
        self.dept_registry.register(self.coding_dept)
        self.dept_registry.register(self.system_dept)

        # Register capabilities (Constitution-aligned bootstrapping)
        register_initial_capabilities(self.cap_registry)
        self.twin.update_capabilities(self.cap_registry.list_capabilities())

        logger.info("✅ All departments registered and capabilities loaded.")

    def run(self, user_input: str):
        """Delegate user request to Executive Mind."""
        logger.info(f"Processing request: {user_input[:100]}...")
        return self.mind.process_request(user_input)

    def dispatch_tasks(self) -> dict:
        """
        Process all active tasks via departments and return completed outputs.
        This is the main loop for task execution.
        """
        results = {}
        for task_id, task in list(self.cos.active_tasks.items()):
            dept = self.dept_registry.get_department(task.assigned_department_id)
            if dept:
                try:
                    dept.process_task(task)
                    if task.status.value == "completed":
                        results[task_id] = task.output_data
                        logger.info(f"Task {task_id} completed by {dept.name}")
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                    # Optionally mark task as failed
                    task.status = "failed"
                    task.output_data = {"error": str(e)}
                    results[task_id] = task.output_data
            else:
                logger.warning(f"Department for task {task_id} not found.")
        return results

    def shutdown(self):
        """Gracefully shutdown the engine (save state, unload model, etc.)"""
        logger.info("Shutting down Cognitive Engine V3...")
        if self.engine:
            self.engine.unload()
        if self.secure_memory:
            # If SecureMemoryStore has a close method
            if hasattr(self.secure_memory, 'close'):
                self.secure_memory.close()
        logger.info("Shutdown complete.")


# ---------- 11. STANDALONE TEST ----------
if __name__ == "__main__":
    # This allows you to test the engine independently
    engine = CognitiveEngineV3()
    print("\n--- JARVIS Cognitive Engine V3: Executive Mind Architecture Online ---")
    response = engine.run("Research the future of decentralized AI")
    print(response)

    # Process the task (simulated dispatch loop)
    results = engine.dispatch_tasks()
    if results:
        print("\n=== Task Results ===")
        for tid, out in results.items():
            print(f"[{tid}]: {out}")
    else:
        print("\nNo tasks completed yet.")

    engine.shutdown()
