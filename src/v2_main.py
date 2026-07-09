import os
import sys

# Ensure the project root is in the path for direct execution
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.event_bus import EventBus
from src.core.registry import DepartmentRegistry, CapabilityRegistry
from src.core.hardware import HardwareManager
from src.core.model_manager import ModelManager
from src.executive.chief_of_staff import ChiefOfStaff
from src.executive.mind import ExecutiveMind
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.core.digital_twin import DigitalTwin
from src.core.bootstrapping import register_initial_capabilities

from src.llm_engine import LLMEngine

class CognitiveEngineV3:
    def __init__(self):
        # 1. Infrastructure
        self.event_bus = EventBus()
        self.dept_registry = DepartmentRegistry()
        self.cap_registry = CapabilityRegistry()
        self.twin = DigitalTwin()

        hardware_info = HardwareManager.detect_hardware()
        self.twin.update_hardware(hardware_info)
        settings = HardwareManager.get_optimized_settings(hardware_info)
        self.model_manager = ModelManager(settings)
        self.engine = LLMEngine() # Initialize core engine

        # 2. Executive Hierarchy
        self.cos = ChiefOfStaff(self.event_bus, self.cap_registry, self.dept_registry)
        # JARVIS V3: Using Executive Mind as the cognitive core
        self.mind = ExecutiveMind(self.cos, self.event_bus, self.twin)

        # 3. Departments
        self.research_dept = ResearchDepartment(self.engine)
        self.coding_dept = CodingDepartment(self.engine)

        # 4. Initialization
        self._setup()

    def _setup(self):
        # Initialize departments
        self.research_dept.initialize(self.event_bus)
        self.coding_dept.initialize(self.event_bus)

        # Register departments
        self.dept_registry.register(self.research_dept)
        self.dept_registry.register(self.coding_dept)

        # Register capabilities (Constitution-aligned bootstrapping)
        register_initial_capabilities(self.cap_registry)
        self.twin.update_capabilities(self.cap_registry.list_capabilities())

    def run(self, user_input: str):
        # Dispatch to the Executive Mind
        return self.mind.process_request(user_input)

    def dispatch_tasks(self) -> dict:
        """
        Simulation of the EventBus/ChiefOfStaff dispatch loop.
        Returns a dictionary of results for any completed tasks.
        """
        results = {}
        for task_id, task in list(self.cos.active_tasks.items()):
            dept = self.dept_registry.get_department(task.assigned_department_id)
            if dept:
                dept.process_task(task)
                if task.status.value == "completed":
                    results[task_id] = task.output_data
        return results

if __name__ == "__main__":
    engine = CognitiveEngineV3()
    print("--- JARVIS Cognitive Engine V3: Executive Mind Architecture Online ---")
    response = engine.run("Research the future of decentralized AI")
    print(response)

    # Process the task
    engine.dispatch_tasks()
