import os
import sys
import logging
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio

import requests

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.event_bus import EventBus
from src.core.registry import DepartmentRegistry, CapabilityRegistry as CapabilityRegistryOld
from src.core.hardware import HardwareManager
from src.core.model_manager import ModelManager
from src.executive.chief_of_staff import ChiefOfStaff
from src.executive.mind import ExecutiveMind
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.departments.system import SystemDepartment
from src.core.digital_twin import DigitalTwin

from src.llm_engine import LLMEngine
from src.core.tools import ToolRegistry, CapabilityDefinition, CapabilityParameter
from src.memory.knowledge_librarian import KnowledgeLibrarian
from src.core.models import ExecutionState

# ---- Capability Platform ----
from src.capabilities import CapabilityRegistry as NewCapabilityRegistry
from src.capabilities.providers import BuiltinProvider
from src.capabilities.resolver import CapabilityResolver
from src.capabilities.execution import CapabilityExecutionEngine
from src.capabilities.context import ExecutionContext
from src.capabilities.budgets import CapabilityBudget

# ---- Cognitive Platform ----
from src.cognition import (
    CognitiveWorkspace,
    AttentionFilter,
    ReflectionEngine,
    LearningEngine,
    KnowledgeStore,
    RecallEngine,
    CognitiveAssistant,
    SleepScheduler,
    CognitiveHealthMonitor,
)
from src.cognition.models import Experience, ExperienceSource, ExperienceType

# ---- Executive Platform ----
from src.executive.state import ExecutiveState
from src.executive.intent import IntentInterpreter
from src.executive.goals import GoalManager
from src.executive.strategy import StrategyEngine
from src.executive.planning import PlanningEngine
from src.executive.decision import DecisionEngine
from src.executive.delegation import DelegationManager
from src.executive.review import ReviewEngine
from src.executive.adaptation import AdaptationEngine

# ---- Environment Platform ----
from src.environment import EnvironmentManager
from src.environment.models import Domain
from src.environment.providers.local import LocalFilesystemProvider
from src.environment.providers.local_calendar import LocalCalendarProvider
from src.environment.providers.services import LocalServicesProvider
from src.environment.providers.local_email import LocalEmailProvider
from src.environment.providers.local_github import LocalGitHubProvider
from src.environment.providers.local_workspace import LocalWorkspaceProvider
from src.environment.providers.local_hardware import LocalHardwareProvider

# ---- Evolution Platform ----
from src.evolution import EvolutionManager

# System Control imports
from src.bridge.synapse import SynapseInterface
from src.core.security import SecurityModule

# Import the Brave search function directly
from src.capabilities.providers.builtin import _brave_search

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
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner

        # ---------- Core Infrastructure ----------
        self.event_bus = EventBus()
        self.dept_registry = DepartmentRegistry()
        self.cap_registry = CapabilityRegistryOld()
        self.twin = DigitalTwin(secure_memory=self.secure_memory)

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

        # ---------- ChiefOfStaff ----------
        self.cos = ChiefOfStaff(
            self.event_bus,
            self.cap_registry,
            self.dept_registry,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
            tool_registry=None,
        )

        # ---------- Tool Registry ----------
        self.tool_registry = ToolRegistry(
            chief_of_staff=self.cos,
            cap_registry=self.cap_registry,
            dept_registry=self.dept_registry,
        )
        self.tool_registry.set_event_bus(self.event_bus)
        self.cos.set_tool_registry(self.tool_registry)

        # ---------- Environment Platform ----------
        self.environment = EnvironmentManager(event_bus=self.event_bus)

        # Register filesystem provider
        allowed_paths = [
            os.path.expanduser("~"),
            project_root,
            "/mnt/jarvis_home",
            "/tmp",
        ]
        local_fs = LocalFilesystemProvider(
            secure_memory=self.secure_memory,
            allowed_paths=allowed_paths,
        )
        self.environment.register_provider("local_fs", local_fs)
        logging.info("✅ Filesystem provider registered.")

        # Register calendar provider
        calendar_provider = LocalCalendarProvider(
            secure_memory=self.secure_memory,
        )
        self.environment.register_provider("local_calendar", calendar_provider)
        logging.info("✅ Calendar provider registered.")

        # Register services provider (weather, news)
        services_provider = LocalServicesProvider(
            secure_memory=self.secure_memory,
        )
        self.environment.register_provider("local_services", services_provider)
        logging.info("✅ Services provider registered.")

        # Register email provider
        email_provider = LocalEmailProvider(
            secure_memory=self.secure_memory,
        )
        self.environment.register_provider("local_email", email_provider)
        logging.info("✅ Email provider registered.")

        # Register GitHub provider
        github_provider = LocalGitHubProvider(
            secure_memory=self.secure_memory,
        )
        self.environment.register_provider("local_github", github_provider)
        logging.info("✅ GitHub provider registered.")

        # Register workspace provider
        workspace_provider = LocalWorkspaceProvider(
            secure_memory=self.secure_memory,
        )
        self.environment.register_provider("local_workspace", workspace_provider)
        logging.info("✅ Workspace provider registered.")

        # Register hardware provider
        hardware_provider = LocalHardwareProvider(
            secure_memory=self.secure_memory,
        )
        self.environment.register_provider("local_hardware", hardware_provider)
        logging.info("✅ Hardware provider registered.")

        # ---------- Evolution Platform ----------
        self.evolution = EvolutionManager(
            root_path=project_root,
            event_bus=self.event_bus,
        )
        logging.info("✅ Evolution Platform initialized.")

        # ---------- Register Capabilities ----------
        self._register_existing_capabilities()
        self._register_calendar_tool()
        self._register_email_tool()
        self._register_email_reader_tool()
        self._register_file_manager_tool()
        self._register_github_tool()
        self._register_tts_tool()
        self._register_news_tool()
        self._register_todo_tool()
        self._register_notes_tool()
        self._register_workspace_tool()
        self._register_hardware_tool()

        logging.info(f"✅ Registered {len(self.tool_registry._capabilities)} capabilities in tool registry.")

        # ---------- Capability Platform ----------
        self.capability_registry = NewCapabilityRegistry()
        self.builtin_provider = BuiltinProvider(self.tool_registry, self.engine)
        self.resolver = CapabilityResolver(self.capability_registry)
        self.execution_engine = CapabilityExecutionEngine(self.capability_registry, self.event_bus.publish)

        manifests = self.builtin_provider.discover()
        for manifest in manifests:
            impl = self.builtin_provider.load(manifest)
            if impl:
                self.capability_registry.register(manifest, impl)

        # ---------- Cognitive Platform ----------
        self.knowledge_store = KnowledgeStore(self.secure_memory) if self.secure_memory else None
        self.workspace = CognitiveWorkspace()
        self.reflection_engine = ReflectionEngine(self.engine)
        self.learning_engine = LearningEngine(self.knowledge_store) if self.knowledge_store else None
        self.recall_engine = RecallEngine(self.knowledge_store) if self.knowledge_store else None
        self.assistant = CognitiveAssistant(self.recall_engine) if self.recall_engine else None
        self.health_monitor = CognitiveHealthMonitor(self.knowledge_store) if self.knowledge_store else None
        self.sleep_scheduler = SleepScheduler(
            reflection_engine=self.reflection_engine,
            learning_engine=self.learning_engine,
            health_monitor=self.health_monitor,
            workspace=self.workspace,
            interval_seconds=3600 * 12,
        ) if all([self.reflection_engine, self.learning_engine, self.health_monitor]) else None

        self.attention_filter = AttentionFilter()
        logging.info("✅ Cognitive Platform initialized.")

        # ---------- Executive Platform ----------
        self.executive_state = ExecutiveState()
        self.intent_interpreter = IntentInterpreter(self.engine)
        self.goal_manager = GoalManager(self.executive_state)
        self.strategy_engine = StrategyEngine(self.engine)
        self.planning_engine = PlanningEngine(self.cap_registry, self.event_bus)
        self.decision_engine = DecisionEngine()
        self.delegation_manager = DelegationManager(self.cos)
        self.review_engine = ReviewEngine()
        self.adaptation_engine = AdaptationEngine(self.executive_state)
        logging.info("✅ Executive Platform initialized.")

        # ---------- Executive Mind ----------
        self.mind = ExecutiveMind(
            chief_of_staff=self.cos,
            event_bus=self.event_bus,
            digital_twin=self.twin,
            engine=self.engine,
            tool_registry=self.tool_registry,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )

        # ---------- Departments ----------
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

        # ---------- Librarian ----------
        self.librarian = KnowledgeLibrarian(
            memory=self.mind.memory,
            secure_memory=self.secure_memory,
            engine=self.engine,
        )

        self._setup()

        if self.sleep_scheduler:
            asyncio.create_task(self.sleep_scheduler.start())
            logging.info("[V2] Sleep scheduler started.")

    # ---------- Registration Methods ----------

    def _register_existing_capabilities(self):
        # Research – with direct handler
        research_cap = CapabilityDefinition(
            name="research_specialist",
            description="Perform deep factual research and evidence collection on any topic.",
            parameters=[
                CapabilityParameter(name="objective", type="string", description="The topic to research", required=True),
                CapabilityParameter(name="depth", type="string", description="Research depth: brief, standard, or comprehensive", required=False, enum=["brief", "standard", "comprehensive"]),
            ],
            handler=_brave_search,
            department="Research",
        )
        self.tool_registry.register(research_cap)

        # Coding
        coding_cap = CapabilityDefinition(
            name="coding_specialist",
            description="Generate, analyze, and optimize source code.",
            parameters=[
                CapabilityParameter(name="objective", type="string", description="Coding task description", required=True),
                CapabilityParameter(name="language", type="string", description="Programming language", required=False),
            ],
            department="Coding",
        )
        self.tool_registry.register(coding_cap)

        # Time
        time_cap = CapabilityDefinition(
            name="time_service",
            description="Retrieve the current system time and date.",
            parameters=[],
            department="System",
        )
        self.tool_registry.register(time_cap)

        # System Info
        sysinfo_cap = CapabilityDefinition(
            name="system_info",
            description="Retrieve hardware statistics and OS status.",
            parameters=[],
            department="System",
        )
        self.tool_registry.register(sysinfo_cap)

        # Weather – now using Environment Platform
        def weather_handler(**kwargs):
            city = kwargs.get('city') or kwargs.get('location') or "London"
            services_provider = self.environment.get_domain_provider(Domain.SERVICES)
            if services_provider is None:
                return {"error": "Services provider not available"}
            try:
                result = services_provider.execute("weather", {"city": city})
                return result
            except Exception as e:
                logger.error(f"Weather error: {e}", exc_info=True)
                return {"error": str(e)}

        weather_cap = CapabilityDefinition(
            name="weather",
            description="Get the current weather for a city using the Environment Platform. Provide the city name.",
            parameters=[
                CapabilityParameter(name="city", type="string", description="Name of the city", required=True),
            ],
            handler=weather_handler,
            department="System",
        )
        self.tool_registry.register(weather_cap)

        # System Control (uses Synapse directly – will be migrated later)
        security_module = SecurityModule(secure_memory=self.secure_memory)
        synapse = SynapseInterface(security_module, secure_memory=self.secure_memory)

        def system_control_handler(**kwargs):
            action = kwargs.get('action')
            command = kwargs.get('command')
            path = kwargs.get('path')
            content = kwargs.get('content')
            if action == "execute":
                if not command:
                    return {"error": "Missing 'command' parameter"}
                result = synapse.execute_command(command)
                return {"output": result}
            elif action == "read_file":
                if not path:
                    return {"error": "Missing 'path' parameter"}
                content = synapse.read_file(path)
                if content is None:
                    return {"error": f"Could not read file {path}"}
                return {"content": content}
            elif action == "write_file":
                if not path or content is None:
                    return {"error": "Missing 'path' or 'content'"}
                success = synapse.write_file(path, content)
                if not success:
                    return {"error": f"Could not write to {path}"}
                return {"success": True}
            else:
                return {"error": f"Unknown action: {action}"}

        system_cap = CapabilityDefinition(
            name="system_control",
            description="Execute system commands, read files, or write files. Use with caution. Actions: 'execute' (requires 'command'), 'read_file' (requires 'path'), 'write_file' (requires 'path' and 'content').",
            parameters=[
                CapabilityParameter(name="action", type="string", description="The action: 'execute', 'read_file', or 'write_file'", required=True, enum=["execute", "read_file", "write_file"]),
                CapabilityParameter(name="command", type="string", description="The system command to execute (for action='execute')", required=False),
                CapabilityParameter(name="path", type="string", description="File path (for read_file or write_file)", required=False),
                CapabilityParameter(name="content", type="string", description="Content to write (for write_file)", required=False),
            ],
            handler=system_control_handler,
            department="System",
        )
        self.tool_registry.register(system_cap)

    def _register_calendar_tool(self):
        def calendar_handler(**kwargs):
            action = kwargs.get('action')
            params = {}
            if action == "add_event":
                params['title'] = kwargs.get('title')
                params['date'] = kwargs.get('date')
                params['description'] = kwargs.get('description')
            elif action == "remove_event":
                params['event_id'] = kwargs.get('event_id') or kwargs.get('id')

            cal_provider = self.environment.get_domain_provider(Domain.CALENDAR)
            if cal_provider is None:
                return {"error": "Calendar provider not available"}
            try:
                result = cal_provider.execute(action, params)
                return result
            except Exception as e:
                logger.error(f"Calendar error: {e}", exc_info=True)
                return {"error": str(e)}

        calendar_cap = CapabilityDefinition(
            name="calendar",
            description="Manage calendar events using the Environment Platform.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action to perform", required=True,
                                    enum=["list_events", "add_event", "remove_event"]),
                CapabilityParameter(name="title", type="string", description="Event title", required=False),
                CapabilityParameter(name="date", type="string", description="Event date (ISO)", required=False),
                CapabilityParameter(name="description", type="string", description="Event description", required=False),
                CapabilityParameter(name="event_id", type="integer", description="Event ID", required=False),
            ],
            handler=calendar_handler,
            department="System",
        )
        self.tool_registry.register(calendar_cap)

    def _register_email_tool(self):
        """
        Email send capability – now uses the Environment Platform.
        """
        def email_handler(**kwargs):
            action = kwargs.get('action')
            if action != "send":
                return {"error": "Only 'send' action is supported"}
            params = {
                'to': kwargs.get('to') or kwargs.get('recipient'),
                'subject': kwargs.get('subject'),
                'body': kwargs.get('body') or kwargs.get('content'),
            }
            email_provider = self.environment.get_domain_provider(Domain.EMAIL)
            if email_provider is None:
                return {"error": "Email provider not available"}
            try:
                result = email_provider.execute("send", params)
                return result
            except Exception as e:
                logger.error(f"Email error: {e}", exc_info=True)
                return {"error": str(e)}

        email_cap = CapabilityDefinition(
            name="email",
            description="Send emails using the Environment Platform.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: 'send'", required=True, enum=["send"]),
                CapabilityParameter(name="to", type="string", description="Recipient email address", required=True),
                CapabilityParameter(name="subject", type="string", description="Email subject", required=True),
                CapabilityParameter(name="body", type="string", description="Email body", required=True),
            ],
            handler=email_handler,
            department="System",
        )
        self.tool_registry.register(email_cap)

    def _register_email_reader_tool(self):
        """
        Email reader capability – now uses the Environment Platform.
        """
        def email_reader_handler(**kwargs):
            action = kwargs.get('action', 'list')
            params = {}
            if action == "list":
                params['limit'] = kwargs.get('limit', 10)
            elif action == "read":
                params['email_id'] = kwargs.get('email_id')

            email_provider = self.environment.get_domain_provider(Domain.EMAIL)
            if email_provider is None:
                return {"error": "Email provider not available"}
            try:
                result = email_provider.execute(action, params)
                return result
            except Exception as e:
                logger.error(f"Email reader error: {e}", exc_info=True)
                return {"error": str(e)}

        email_reader_cap = CapabilityDefinition(
            name="email_reader",
            description="Read emails using the Environment Platform.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: 'list' or 'read'", required=True, enum=["list", "read"]),
                CapabilityParameter(name="limit", type="integer", description="Number of emails to list (default 10)", required=False),
                CapabilityParameter(name="email_id", type="string", description="Email ID to read", required=False),
            ],
            handler=email_reader_handler,
            department="System",
        )
        self.tool_registry.register(email_reader_cap)

    def _register_file_manager_tool(self):
        def file_manager_handler(**kwargs):
            action = kwargs.get('action')
            path = kwargs.get('path') or kwargs.get('directory')
            content = kwargs.get('content')
            src = kwargs.get('src')
            dst = kwargs.get('dst')
            pattern = kwargs.get('pattern')
            recursive = kwargs.get('recursive', True)

            fs_provider = self.environment.get_domain_provider(Domain.FILESYSTEM)
            if fs_provider is None:
                return {"error": "Filesystem provider not available"}

            try:
                params = {}
                if path is not None:
                    params['path'] = path
                if content is not None:
                    params['content'] = content
                if src is not None:
                    params['src'] = src
                if dst is not None:
                    params['dst'] = dst
                if pattern is not None:
                    params['pattern'] = pattern
                if recursive is not None:
                    params['recursive'] = recursive

                result = fs_provider.execute(action, params)
                return result
            except Exception as e:
                logger.error(f"File manager error: {e}", exc_info=True)
                return {"error": str(e)}

        file_manager_cap = CapabilityDefinition(
            name="file_manager",
            description="Manage files and directories using the Environment Platform.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action", required=True,
                                    enum=["list", "read", "write", "delete", "mkdir", "copy", "move", "metadata", "search"]),
                CapabilityParameter(name="path", type="string", description="Path", required=False),
                CapabilityParameter(name="content", type="string", description="Content", required=False),
                CapabilityParameter(name="src", type="string", description="Source", required=False),
                CapabilityParameter(name="dst", type="string", description="Destination", required=False),
                CapabilityParameter(name="pattern", type="string", description="Search pattern", required=False),
                CapabilityParameter(name="recursive", type="boolean", description="Recursive", required=False),
            ],
            handler=file_manager_handler,
            department="System",
        )
        self.tool_registry.register(file_manager_cap)

    def _register_github_tool(self):
        """
        GitHub capability – now uses the Environment Platform.
        """
        def github_handler(**kwargs):
            action = kwargs.get('action')
            params = {k: v for k, v in kwargs.items() if k != 'action'}

            github_provider = self.environment.get_provider("local_github")
            if github_provider is None:
                return {"error": "GitHub provider not available"}
            try:
                result = github_provider.execute(action, params)
                return result
            except Exception as e:
                logger.error(f"GitHub error: {e}", exc_info=True)
                return {"error": str(e)}

        github_cap = CapabilityDefinition(
            name="github",
            description="Interact with GitHub using the Environment Platform.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action", required=True,
                                    enum=["list_repos", "create_repo", "get_file", "create_issue", "push"]),
                CapabilityParameter(name="repo", type="string", description="Repository name", required=False),
                CapabilityParameter(name="path", type="string", description="File path", required=False),
                CapabilityParameter(name="title", type="string", description="Issue title", required=False),
                CapabilityParameter(name="body", type="string", description="Issue body", required=False),
                CapabilityParameter(name="branch", type="string", description="Branch name", required=False),
                CapabilityParameter(name="message", type="string", description="Commit message", required=False),
                CapabilityParameter(name="files", type="object", description="Files to push", required=False),
            ],
            handler=github_handler,
            department="System",
        )
        self.tool_registry.register(github_cap)

    def _register_tts_tool(self):
        def tts_handler(**kwargs):
            text = kwargs.get('text')
            if not text:
                return {"error": "Missing 'text'"}
            tts_url = os.getenv("TTS_URL", "http://localhost:5051/v1/audio/speech")
            tts_api_key = os.getenv("TTS_API_KEY", "your_tts_key")
            voice = kwargs.get('voice', "alloy")
            response_format = kwargs.get('response_format', "mp3")
            speed = kwargs.get('speed', 1.0)

            try:
                resp = requests.post(
                    tts_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {tts_api_key}",
                    },
                    json={
                        "input": text,
                        "voice": voice,
                        "response_format": response_format,
                        "speed": speed,
                    },
                    timeout=30,
                )
                if resp.status_code != 200:
                    return {"error": f"TTS error: {resp.text}"}
                output_path = kwargs.get('output_path', f"speech.{response_format}")
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return {
                    "output_path": output_path,
                    "message": f"Speech generated and saved to {output_path}",
                }
            except Exception as e:
                return {"error": str(e)}

        tts_cap = CapabilityDefinition(
            name="text_to_speech",
            description="Convert text to speech using Edge TTS.",
            parameters=[
                CapabilityParameter(name="text", type="string", description="Text to speak", required=True),
                CapabilityParameter(name="voice", type="string", description="Voice", required=False),
                CapabilityParameter(name="response_format", type="string", description="Audio format", required=False),
                CapabilityParameter(name="speed", type="number", description="Speed", required=False),
                CapabilityParameter(name="output_path", type="string", description="Output path", required=False),
            ],
            handler=tts_handler,
            department="System",
        )
        self.tool_registry.register(tts_cap)

    def _register_news_tool(self):
        def news_handler(**kwargs):
            topic = kwargs.get('topic', "technology")
            services_provider = self.environment.get_domain_provider(Domain.SERVICES)
            if services_provider is None:
                return {"error": "Services provider not available"}
            try:
                result = services_provider.execute("news", {"topic": topic})
                return result
            except Exception as e:
                logger.error(f"News error: {e}", exc_info=True)
                return {"error": str(e)}

        news_cap = CapabilityDefinition(
            name="news",
            description="Get the latest news headlines using the Environment Platform.",
            parameters=[
                CapabilityParameter(name="topic", type="string", description="Topic", required=False),
            ],
            handler=news_handler,
            department="System",
        )
        self.tool_registry.register(news_cap)

    def _register_todo_tool(self):
        TODO_FILE = os.path.join(project_root, "data", "todos.json")

        def _load_todos():
            if not os.path.exists(TODO_FILE):
                return []
            try:
                with open(TODO_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []

        def _save_todos(todos):
            os.makedirs(os.path.dirname(TODO_FILE), exist_ok=True)
            with open(TODO_FILE, 'w') as f:
                json.dump(todos, f, indent=2)

        def todo_handler(**kwargs):
            action = kwargs.get('action')
            if action == "list":
                todos = _load_todos()
                return {"todos": todos}
            elif action == "add":
                title = kwargs.get('title') or kwargs.get('task')
                if not title:
                    return {"error": "Missing 'title'"}
                todos = _load_todos()
                new_id = max([t.get("id", 0) for t in todos]) + 1 if todos else 1
                todo = {"id": new_id, "title": title, "completed": False}
                todos.append(todo)
                _save_todos(todos)
                return {"todo": todo, "message": "Todo added"}
            elif action == "complete":
                todo_id = kwargs.get('id')
                if todo_id is None:
                    return {"error": "Missing 'id'"}
                todos = _load_todos()
                for t in todos:
                    if t.get("id") == todo_id:
                        t["completed"] = True
                        _save_todos(todos)
                        return {"todo": t, "message": "Todo marked as complete"}
                return {"error": "Todo not found"}
            elif action == "delete":
                todo_id = kwargs.get('id')
                if todo_id is None:
                    return {"error": "Missing 'id'"}
                todos = _load_todos()
                new_todos = [t for t in todos if t.get("id") != todo_id]
                if len(new_todos) == len(todos):
                    return {"error": "Todo not found"}
                _save_todos(new_todos)
                return {"message": "Todo deleted"}
            else:
                return {"error": f"Unknown action: {action}"}

        todo_cap = CapabilityDefinition(
            name="todo",
            description="Manage your todo list.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action", required=True,
                                    enum=["list", "add", "complete", "delete"]),
                CapabilityParameter(name="title", type="string", description="Title", required=False),
                CapabilityParameter(name="id", type="integer", description="Todo ID", required=False),
            ],
            handler=todo_handler,
            department="System",
        )
        self.tool_registry.register(todo_cap)

    def _register_notes_tool(self):
        NOTES_FILE = os.path.join(project_root, "data", "notes.json")

        def _load_notes():
            if not os.path.exists(NOTES_FILE):
                return []
            try:
                with open(NOTES_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []

        def _save_notes(notes):
            os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)
            with open(NOTES_FILE, 'w') as f:
                json.dump(notes, f, indent=2)

        def notes_handler(**kwargs):
            action = kwargs.get('action')
            if action == "list":
                notes = _load_notes()
                return {"notes": notes}
            elif action == "create":
                title = kwargs.get('title')
                content = kwargs.get('content')
                if not title or not content:
                    return {"error": "Missing 'title' or 'content'"}
                notes = _load_notes()
                new_id = max([n.get("id", 0) for n in notes]) + 1 if notes else 1
                note = {"id": new_id, "title": title, "content": content, "created_at": datetime.now().isoformat()}
                notes.append(note)
                _save_notes(notes)
                return {"note": note, "message": "Note created"}
            elif action == "read":
                note_id = kwargs.get('id')
                if note_id is None:
                    return {"error": "Missing 'id'"}
                notes = _load_notes()
                for n in notes:
                    if n.get("id") == note_id:
                        return {"note": n}
                return {"error": "Note not found"}
            elif action == "update":
                note_id = kwargs.get('id')
                title = kwargs.get('title')
                content = kwargs.get('content')
                if note_id is None:
                    return {"error": "Missing 'id'"}
                if not title and not content:
                    return {"error": "Missing 'title' or 'content' to update"}
                notes = _load_notes()
                for n in notes:
                    if n.get("id") == note_id:
                        if title:
                            n["title"] = title
                        if content:
                            n["content"] = content
                        n["updated_at"] = datetime.now().isoformat()
                        _save_notes(notes)
                        return {"note": n, "message": "Note updated"}
                return {"error": "Note not found"}
            elif action == "delete":
                note_id = kwargs.get('id')
                if note_id is None:
                    return {"error": "Missing 'id'"}
                notes = _load_notes()
                new_notes = [n for n in notes if n.get("id") != note_id]
                if len(new_notes) == len(notes):
                    return {"error": "Note not found"}
                _save_notes(new_notes)
                return {"message": "Note deleted"}
            else:
                return {"error": f"Unknown action: {action}"}

        notes_cap = CapabilityDefinition(
            name="notes",
            description="Manage notes.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action", required=True,
                                    enum=["list", "create", "read", "update", "delete"]),
                CapabilityParameter(name="title", type="string", description="Title", required=False),
                CapabilityParameter(name="content", type="string", description="Content", required=False),
                CapabilityParameter(name="id", type="integer", description="Note ID", required=False),
            ],
            handler=notes_handler,
            department="System",
        )
        self.tool_registry.register(notes_cap)

    def _register_workspace_tool(self):
        """
        Workspace capability – provides workspace awareness via the Environment Platform.
        """
        def workspace_handler(**kwargs):
            action = kwargs.get('action', 'status')
            params = {k: v for k, v in kwargs.items() if k != 'action'}

            workspace_provider = self.environment.get_domain_provider(Domain.WORKSPACE)
            if workspace_provider is None:
                return {"error": "Workspace provider not available"}

            try:
                result = workspace_provider.execute(action, params)
                return result
            except Exception as e:
                logger.error(f"Workspace error: {e}", exc_info=True)
                return {"error": str(e)}

        workspace_cap = CapabilityDefinition(
            name="workspace",
            description="Get workspace information (active window, clipboard, processes, etc.).",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: status, active_window, clipboard, processes, current_directory", required=True,
                                    enum=["status", "active_window", "clipboard", "processes", "current_directory"]),
                CapabilityParameter(name="limit", type="integer", description="Limit for processes list", required=False),
            ],
            handler=workspace_handler,
            department="System",
        )
        self.tool_registry.register(workspace_cap)

    def _register_hardware_tool(self):
        """
        Hardware capability – provides hardware and network info.
        """
        def hardware_handler(**kwargs):
            action = kwargs.get('action', 'status')
            params = {k: v for k, v in kwargs.items() if k != 'action'}

            hardware_provider = self.environment.get_domain_provider(Domain.HARDWARE)
            if hardware_provider is None:
                return {"error": "Hardware provider not available"}

            try:
                result = hardware_provider.execute(action, params)
                return result
            except Exception as e:
                logger.error(f"Hardware error: {e}", exc_info=True)
                return {"error": str(e)}

        hardware_cap = CapabilityDefinition(
            name="hardware",
            description="Get hardware and network information.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: status, cpu, memory, disk, battery, network, ping", required=True,
                                    enum=["status", "cpu", "memory", "disk", "battery", "network", "ping"]),
                CapabilityParameter(name="path", type="string", description="Disk path (for disk action)", required=False),
                CapabilityParameter(name="host", type="string", description="Host to ping", required=False),
            ],
            handler=hardware_handler,
            department="System",
        )
        self.tool_registry.register(hardware_cap)

    # ---------- Setup ----------
    def _setup(self):
        self.research_dept.initialize(self.event_bus)
        self.coding_dept.initialize(self.event_bus)
        self.system_dept.initialize(self.event_bus)

        self.dept_registry.register(self.research_dept)
        self.dept_registry.register(self.coding_dept)
        self.dept_registry.register(self.system_dept)

        logger.info(f"[V2] Syncing {len(self.tool_registry._capabilities)} capabilities to old registry...")
        from src.core.models import Capability
        for cap_def in self.tool_registry._capabilities.values():
            cap_obj = Capability(
                name=cap_def.name,
                purpose=cap_def.description,
                inputs={p.name: p.description for p in cap_def.parameters},
                outputs={},
                estimated_time_sec=0,
            )
            self.cap_registry.register(cap_obj, cap_def.department or "System")
            logger.info(f"[V2] Registered capability '{cap_def.name}' to department '{cap_def.department or 'System'}' in old registry.")

        self.twin.update_capabilities(self.cap_registry.list_capabilities())
        logger.info(f"[V2] Old registry now has {len(self.cap_registry.list_capabilities())} capabilities.")

        logging.info("✅ All departments and capabilities registered.")

    # ---------- Public Methods ----------
    def run(self, user_input: str, user_id: str = "default", force_agent: bool = False):
        return self.mind.process_request(user_input, user_id=user_id, collect_trace=True, force_agent=force_agent)

    def dispatch_tasks(self) -> dict:
        results = {}
        for task_id, task in list(self.cos.active_tasks.items()):
            dept = self.dept_registry.get_department(task.assigned_department_id)
            if dept:
                dept.process_task(task)
                if task.state == ExecutionState.COMPLETED:
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
        if hasattr(self, 'environment'):
            self.environment.shutdown()
        if hasattr(self, 'evolution'):
            # Nothing to shut down yet
            pass
        if self.secure_memory and hasattr(self.secure_memory, 'close'):
            self.secure_memory.close()
        if self.sleep_scheduler:
            asyncio.create_task(self.sleep_scheduler.stop())
        for dept in [self.research_dept, self.coding_dept, self.system_dept]:
            if hasattr(dept, 'shutdown'):
                dept.shutdown()


if __name__ == "__main__":
    engine = CognitiveEngineV3()
    print("--- JARVIS Cognitive Engine V3 Online ---")
    response, trace = engine.run("Research the future of decentralized AI")
    print(response)
    print("Trace:", trace)
    engine.dispatch_tasks()
