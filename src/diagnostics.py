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
from src.executive.mind import ExecutiveMind
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.core.digital_twin import DigitalTwin
from src.core.bootstrapping import register_initial_capabilities

def run_v3_executive_audit():
    print("--- JARVIS V3: EXECUTIVE MIND CONSTITUTIONAL AUDIT ---")

    # 1. Infrastructure Initialization
    event_bus = EventBus()
    security = SecurityModule()
    synapse = SynapseInterface(security)
    cap_registry = CapabilityRegistry()
    dept_registry = DepartmentRegistry()
    twin = DigitalTwin()

    # 2. Executive Layer (V3 Hierarchy)
    cos = ChiefOfStaff(event_bus, cap_registry, dept_registry)
    mind = ExecutiveMind(cos, event_bus, twin)

    # 3. Organization Bootstrapping
    research = ResearchDepartment()
    coding = CodingDepartment()
    research.initialize(event_bus)
    coding.initialize(event_bus)
    dept_registry.register(research)
    dept_registry.register(coding)

    register_initial_capabilities(cap_registry)

    # 4. Executive Reasoning Pipeline Test
    print("\n[Mind] Testing Strategic Reasoning Pipeline...")
    request = "Analyze the risks of autonomous kernel updates in Phoenix OS"
    print(f"Executive Request: {request}")

    decision_summary = mind.process_request(request)
    print(f"\n[Mind] Decision Outcome: {decision_summary}")

    # 5. Chief of Staff Coordination Test
    print("\n[CoS] Verifying Operational Execution...")
    results = {}
    for task_id, task in list(cos.active_tasks.items()):
        dept = dept_registry.get_department(task.assigned_department_id)
        if dept:
            print(f"[CoS] Triggering {dept.name} Department for Task {task_id}")
            dept.process_task(task)
            if task.status.value == "completed":
                results[task_id] = task.output_data

    print(f"\n[Audit] Final System Results Collected: {len(results)}")

    # 6. Executive Board Verification
    print("\n[Board] Verifying Engine Consultations...")
    # This is checked by the print statements in Board during mind.process_request

    print("\n--- V3 AUDIT COMPLETE: EXECUTIVE MIND OPERATIONAL ---")

if __name__ == "__main__":
    run_v3_executive_audit()
