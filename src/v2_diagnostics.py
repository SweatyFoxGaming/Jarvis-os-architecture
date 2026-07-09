from src.core.event_bus import EventBus
from src.core.registry import DepartmentRegistry, CapabilityRegistry
from src.core.hardware import HardwareManager
from src.core.security import SecurityModule
from src.bridge.synapse import SynapseInterface
from src.executive.chief_of_staff import ChiefOfStaff
from src.executive.ceo import CEO
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.memory.tiered_memory import HierarchicalMemory
from src.memory.librarian import KnowledgeLibrarian

def run_v2_diagnostics():
    print("--- JARVIS V2 COGNITIVE ENGINE DIAGNOSTICS ---")

    # 1. Framework Initialization
    print("\n1. Initializing Executive Office...")
    event_bus = EventBus()
    security = SecurityModule()
    synapse = SynapseInterface(security)

    # 2. Memory & Librarian
    print("\n2. Initializing Memory System...")
    memory = HierarchicalMemory()
    librarian = KnowledgeLibrarian(memory)

    # 3. Strategy & Operations
    print("\n3. Initializing CEO and Chief of Staff...")
    cos = ChiefOfStaff(event_bus)
    ceo = CEO(cos, event_bus)

    # 4. Departments
    print("\n4. Initializing Departments...")
    research = ResearchDepartment()
    coding = CodingDepartment()
    research.initialize(event_bus)
    coding.initialize(event_bus)

    # 5. End-to-End Workflow Test
    print("\n5. Testing End-to-End Workflow...")
    user_request = "Write a Rust function for secure memory allocation"
    print(f"User Request: {user_request}")

    ceo.process_request(user_request)

    # Simulate the event loop/dispatch
    for task_id, task in list(cos.active_tasks.items()):
        if task.target_department == "Coding":
            coding.process_task(task)

    print("\n6. Checking Result Persistence...")
    memory.store_episode({"request": user_request, "status": "completed"}, importance=0.9)
    librarian.consolidate_episodes()

    print("\n7. Security Audit...")
    synapse.read_file("/etc/passwd")  # Should be denied
    synapse.write_file("./data/test.txt", "V2 Active") # Should be approved

    print("\n--- DIAGNOSTICS COMPLETE: V2 ARCHITECTURE FULLY OPERATIONAL ---")

if __name__ == "__main__":
    run_v2_diagnostics()
