from src.core.event_bus import EventBus
from src.core.registry import DepartmentRegistry, CapabilityRegistry
from src.core.hardware import HardwareManager
from src.core.model_manager import ModelManager
from src.executive.chief_of_staff import ChiefOfStaff
from src.executive.ceo import CEO
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment

from src.llm_engine import LLMEngine

class CognitiveEngineV2:
    def __init__(self):
        # 1. Infrastructure
        self.event_bus = EventBus()
        self.dept_registry = DepartmentRegistry()
        self.cap_registry = CapabilityRegistry()

        hardware_info = HardwareManager.detect_hardware()
        settings = HardwareManager.get_optimized_settings(hardware_info)
        self.model_manager = ModelManager(settings)
        self.engine = LLMEngine() # Initialize core engine

        # 2. Executive Layer
        self.cos = ChiefOfStaff(self.event_bus)
        self.ceo = CEO(self.cos, self.event_bus)

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

        # Register capabilities
        self.cap_registry.register_capability("research", "Research")
        self.cap_registry.register_capability("coding", "Coding")

    def run(self, user_input: str):
        return self.ceo.process_request(user_input)

    def dispatch_tasks(self):
        """
        Simulation of the EventBus/ChiefOfStaff dispatch loop.
        In a real system, this would be reactive.
        """
        for task_id, task in list(self.cos.active_tasks.items()):
            dept = self.dept_registry.get_department(task.target_department)
            if dept:
                dept.process_task(task)

if __name__ == "__main__":
    engine = CognitiveEngineV2()
    print("--- JARVIS Cognitive Engine V2 Online ---")
    response = engine.run("Research memory allocation in Rust")
    print(response)

    # Process the task
    engine.dispatch_tasks()
