import os
import sys
import logging
import requests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
from src.departments.system import SystemDepartment
from src.core.digital_twin import DigitalTwin
from src.core.bootstrapping import register_initial_capabilities

from src.llm_engine import LLMEngine
from src.core.tools import ToolRegistry, ToolDefinition, ToolParameter
from src.memory.knowledge_librarian import KnowledgeLibrarian

# ----- System Control imports -----
from src.bridge.synapse import SynapseInterface
from src.core.security import SecurityModule

# Secure components imports (now passed as parameters)
try:
    from config.secure_config import AppConfig
    AppConfig.load()
except Exception:
    pass

try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None


class CognitiveEngineV3:
    def __init__(self, secure_memory=None, secure_runner=None):
        """
        Initialize the engine with optional secure components.
        """
        # 1. Infrastructure
        self.event_bus = EventBus()
        self.dept_registry = DepartmentRegistry()
        self.cap_registry = CapabilityRegistry()
        self.twin = DigitalTwin()

        # Attach secure memory to components that support it
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner

        if self.secure_memory:
            self.event_bus.set_secure_memory(self.secure_memory)
            self.dept_registry.set_secure_memory(self.secure_memory)
            self.cap_registry.set_secure_memory(self.secure_memory)
            self.twin.set_secure_memory(self.secure_memory)
            logging.info("[V2] Secure memory attached to infrastructure.")

        hardware_info = HardwareManager.detect_hardware()
        self.twin.update_hardware(hardware_info)
        settings = HardwareManager.get_optimized_settings(hardware_info)
        self.model_manager = ModelManager(settings)
        self.engine = LLMEngine()

        # 2. Executive Hierarchy
        self.cos = ChiefOfStaff(
            self.event_bus,
            self.cap_registry,
            self.dept_registry,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )

        # ---------- Tool Registry Setup ----------
        self.tool_registry = ToolRegistry(
            chief_of_staff=self.cos,
            cap_registry=self.cap_registry,
            dept_registry=self.dept_registry,
        )
        self.tool_registry.set_event_bus(self.event_bus)

        # Register Research tool
        research_tool = ToolDefinition(
            name="research_specialist",
            description="Perform deep factual research and evidence collection on any topic.",
            parameters=[
                ToolParameter(
                    name="objective",
                    type="string",
                    description="The topic to research",
                    required=True,
                ),
                ToolParameter(
                    name="depth",
                    type="string",
                    description="Research depth: brief, standard, or comprehensive",
                    required=False,
                    enum=["brief", "standard", "comprehensive"],
                ),
            ],
            department="Research",
        )
        self.tool_registry.register_tool(research_tool)

        # Register Coding tool
        coding_tool = ToolDefinition(
            name="coding_specialist",
            description="Generate, analyze, and optimize source code.",
            parameters=[
                ToolParameter(
                    name="objective",
                    type="string",
                    description="Coding task description",
                    required=True,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Programming language (python, rust, javascript, etc.)",
                    required=False,
                ),
            ],
            department="Coding",
        )
        self.tool_registry.register_tool(coding_tool)

        # Register System Time tool
        time_tool = ToolDefinition(
            name="time_service",
            description="Retrieve the current system time and date.",
            parameters=[],
            department="System",
        )
        self.tool_registry.register_tool(time_tool)

        # Register System Info tool
        sysinfo_tool = ToolDefinition(
            name="system_info",
            description="Retrieve hardware statistics and OS status.",
            parameters=[],
            department="System",
        )
        self.tool_registry.register_tool(sysinfo_tool)

        # ---------- Weather Tool ----------
        def get_weather(params: dict) -> dict:
            city = params.get("city", "London")
            try:
                url = f"https://wttr.in/{city}?format=%C+%t&lang=en"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return {"weather": response.text.strip()}
                else:
                    return {"error": f"HTTP {response.status_code}"}
            except Exception as e:
                return {"error": str(e)}

        weather_tool = ToolDefinition(
            name="weather",
            description="Get the current weather for a city. Provide the city name.",
            parameters=[
                ToolParameter(
                    name="city",
                    type="string",
                    description="Name of the city (e.g., London, Paris, Tokyo)",
                    required=True,
                ),
            ],
            handler=get_weather,
        )
        self.tool_registry.register_tool(weather_tool)

        # ---------- NEW: System Control Tool ----------
        # Create security module and synapse interface (with secure memory if available)
        security_module = SecurityModule(secure_memory=self.secure_memory)
        synapse = SynapseInterface(security_module, secure_memory=self.secure_memory)

        def system_control_handler(params: dict) -> dict:
            """Execute system operations: run command, read file, write file."""
            action = params.get("action")
            if action == "execute":
                command = params.get("command")
                if not command:
                    return {"error": "Missing 'command' parameter"}
                result = synapse.execute_command(command)
                return {"output": result}
            elif action == "read_file":
                path = params.get("path")
                if not path:
                    return {"error": "Missing 'path' parameter"}
                content = synapse.read_file(path)
                if content is None:
                    return {"error": f"Could not read file {path}"}
                return {"content": content}
            elif action == "write_file":
                path = params.get("path")
                content = params.get("content")
                if not path or content is None:
                    return {"error": "Missing 'path' or 'content'"}
                success = synapse.write_file(path, content)
                if not success:
                    return {"error": f"Could not write to {path}"}
                return {"success": True}
            else:
                return {"error": f"Unknown action: {action}"}

        system_tool = ToolDefinition(
            name="system_control",
            description="Execute system commands, read files, or write files. Use with caution. Actions: 'execute' (requires 'command'), 'read_file' (requires 'path'), 'write_file' (requires 'path' and 'content').",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="The action: 'execute', 'read_file', or 'write_file'",
                    required=True,
                    enum=["execute", "read_file", "write_file"],
                ),
                ToolParameter(
                    name="command",
                    type="string",
                    description="The system command to execute (for action='execute')",
                    required=False,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="File path (for read_file or write_file)",
                    required=False,
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write (for write_file)",
                    required=False,
                ),
            ],
            handler=system_control_handler,
        )
        self.tool_registry.register_tool(system_tool)

        logging.info(f"✅ Registered {len(self.tool_registry._tools)} tools (including system_control).")

        # Executive Mind
        self.mind = ExecutiveMind(
            self.cos,
            self.event_bus,
            self.twin,
            engine=self.engine,
            tool_registry=self.tool_registry,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )

        # 3. Departments
        self.research_dept = ResearchDepartment(
            engine=self.engine,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )
        self.coding_dept = CodingDepartment(
            engine=self.engine,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )
        self.system_dept = SystemDepartment(
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )

        # 4. Knowledge Librarian
        self.librarian = KnowledgeLibrarian(
            memory=self.mind.memory,
            secure_memory=self.secure_memory,
            engine=self.engine,
        )

        # 5. Initialization
        self._setup()

    def _setup(self):
        self.research_dept.initialize(self.event_bus)
        self.coding_dept.initialize(self.event_bus)
        self.system_dept.initialize(self.event_bus)

        self.dept_registry.register(self.research_dept)
        self.dept_registry.register(self.coding_dept)
        self.dept_registry.register(self.system_dept)

        register_initial_capabilities(self.cap_registry)
        self.twin.update_capabilities(self.cap_registry.list_capabilities())

        logging.info("✅ All departments and capabilities registered.")

    def run(self, user_input: str, user_id: str = "default"):
        return self.mind.process_request(user_input, user_id=user_id)

    def dispatch_tasks(self) -> dict:
        results = {}
        for task_id, task in list(self.cos.active_tasks.items()):
            dept = self.dept_registry.get_department(task.assigned_department_id)
            if dept:
                dept.process_task(task)
                if task.status.value == "completed":
                    results[task_id] = task.output_data
        return results

    def consolidate_memory(self):
        if hasattr(self, 'librarian') and self.librarian:
            return self.librarian.consolidate_episodes()
        else:
            logging.warning("Librarian not available.")
            return 0

    def shutdown(self):
        logging.info("Shutting down Cognitive Engine V3...")
        if self.engine:
            self.engine.unload()
        if hasattr(self, 'tool_registry'):
            self.tool_registry.shutdown()
        if hasattr(self, 'cos'):
            self.cos.shutdown()
        if hasattr(self, 'librarian'):
            self.librarian.shutdown()
        if self.secure_memory and hasattr(self.secure_memory, 'close'):
            self.secure_memory.close()
        for dept in [self.research_dept, self.coding_dept, self.system_dept]:
            if hasattr(dept, 'shutdown'):
                dept.shutdown()


if __name__ == "__main__":
    engine = CognitiveEngineV3()
    print("--- JARVIS Cognitive Engine V3: Executive Mind Architecture Online ---")
    response = engine.run("Research the future of decentralized AI")
    print(response)
    engine.dispatch_tasks()
