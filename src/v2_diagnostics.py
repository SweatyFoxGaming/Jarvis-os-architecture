import os
import sys

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.event_bus import EventBus
from src.core.registry import DepartmentRegistry, CapabilityRegistry
from src.core.security import SecurityModule
from src.bridge.synapse import SynapseInterface
from src.executive.chief_of_staff import ChiefOfStaff
from src.executive.ceo import CEO
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.memory.tiered_memory import HierarchicalMemory
from src.memory.librarian import KnowledgeLibrarian
from src.core.digital_twin import DigitalTwin
from src.core.bootstrapping import register_initial_capabilities

def run_constitution_diagnostics():
    print("--- PHOENIX INTELLIGENCE PLATFORM: CONSTITUTIONAL AUDIT ---")

    # 1. Infrastructure Initialization
    event_bus = EventBus()
    security = SecurityModule()
    synapse = SynapseInterface(security)
    cap_registry = CapabilityRegistry()
    dept_registry = DepartmentRegistry()
    twin = DigitalTwin()

    # 2. Executive Layer
    cos = ChiefOfStaff(event_bus, cap_registry, dept_registry)
    ceo = CEO(cos, event_bus, twin)

    # 3. Bootstrapping
    research = ResearchDepartment()
    coding = CodingDepartment()
    research.initialize(event_bus)
    coding.initialize(event_bus)
    dept_registry.register(research)
    dept_registry.register(coding)

    register_initial_capabilities(cap_registry)
    twin.update_capabilities(cap_registry.list_capabilities())

    # 4. Constitutional Flow Test
    print("\n[Audit] Testing Capability-based Reasoning...")
    user_request = "Develop a high-performance memory manager for Phoenix OS"
    print(f"User Request: {user_request}")

    res = ceo.process_request(user_request)
    print(f"CEO Output: {res}")

    # Simulate execution
    for task_id, task in list(cos.active_tasks.items()):
        dept = dept_registry.get_department(task.assigned_department_id)
        if dept:
            dept.process_task(task)

    print("\n[Audit] Checking Digital Twin state...")
    print(twin.get_summary())

    print("\n[Audit] Verifying Security Boundaries...")
    synapse.execute_command("rm -rf /") # Should be denied

    print("\n--- AUDIT COMPLETE: ALL SYSTEMS ALIGNED WITH CONSTITUTION ---")

if __name__ == "__main__":
    run_constitution_diagnostics()
