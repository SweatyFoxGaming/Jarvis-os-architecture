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

# ---- Capability Platform imports ----
from src.capabilities import CapabilityRegistry as NewCapabilityRegistry
from src.capabilities.providers import BuiltinProvider
from src.capabilities.resolver import CapabilityResolver
from src.capabilities.execution import CapabilityExecutionEngine
from src.capabilities.context import ExecutionContext
from src.capabilities.budgets import CapabilityBudget
# ---- End Capability Platform imports ----

# ---- Cognitive Platform imports ----
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
# ---- End Cognitive Platform imports ----

# ---- Executive Platform imports ----
from src.executive.state import ExecutiveState
from src.executive.intent import IntentInterpreter
from src.executive.goals import GoalManager
from src.executive.strategy import StrategyEngine
from src.executive.planning import PlanningEngine
from src.executive.decision import DecisionEngine
from src.executive.delegation import DelegationManager
from src.executive.review import ReviewEngine
from src.executive.adaptation import AdaptationEngine
# ---- End Executive Platform imports ----

# System Control imports
from src.bridge.synapse import SynapseInterface
from src.core.security import SecurityModule

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

        # ---------- Create ChiefOfStaff first (without tool_registry) ----------
        self.cos = ChiefOfStaff(
            self.event_bus,
            self.cap_registry,
            self.dept_registry,
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
            tool_registry=None,
        )

        # ---------- Tool Registry (Capability Registry) ----------
        self.tool_registry = ToolRegistry(
            chief_of_staff=self.cos,
            cap_registry=self.cap_registry,
            dept_registry=self.dept_registry,
        )
        self.tool_registry.set_event_bus(self.event_bus)
        self.cos.set_tool_registry(self.tool_registry)

        # ---------- Register All Capabilities ----------
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

        # Departments
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

        # Librarian
        self.librarian = KnowledgeLibrarian(
            memory=self.mind.memory,
            secure_memory=self.secure_memory,
            engine=self.engine,
        )

        self._setup()

        if self.sleep_scheduler:
            asyncio.create_task(self.sleep_scheduler.start())
            logging.info("[V2] Sleep scheduler started.")

    # ---------- Registration Methods with Updated Handlers ----------

    def _register_existing_capabilities(self):
        # Research
        research_cap = CapabilityDefinition(
            name="research_specialist",
            description="Perform deep factual research and evidence collection on any topic.",
            parameters=[
                CapabilityParameter(name="objective", type="string", description="The topic to research", required=True),
                CapabilityParameter(name="depth", type="string", description="Research depth: brief, standard, or comprehensive", required=False, enum=["brief", "standard", "comprehensive"]),
            ],
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

        # Weather
        def get_weather(**kwargs):
            # Accept various parameter names
            city = kwargs.get('city') or kwargs.get('location') or "London"
            try:
                url = f"https://wttr.in/{city}?format=%C+%t&lang=en"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return {"weather": response.text.strip()}
                else:
                    return {"error": f"HTTP {response.status_code}"}
            except Exception as e:
                return {"error": str(e)}

        weather_cap = CapabilityDefinition(
            name="weather",
            description="Get the current weather for a city. Provide the city name.",
            parameters=[
                CapabilityParameter(name="city", type="string", description="Name of the city", required=True),
            ],
            handler=get_weather,
        )
        self.tool_registry.register(weather_cap)

        # System Control
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
        )
        self.tool_registry.register(system_cap)

    def _register_calendar_tool(self):
        CALENDAR_FILE = os.path.join(project_root, "data", "calendar.json")

        def _load_calendar():
            if not os.path.exists(CALENDAR_FILE):
                return []
            try:
                with open(CALENDAR_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []

        def _save_calendar(events):
            os.makedirs(os.path.dirname(CALENDAR_FILE), exist_ok=True)
            with open(CALENDAR_FILE, 'w') as f:
                json.dump(events, f, indent=2)

        def calendar_handler(**kwargs):
            action = kwargs.get('action')
            if action == "list_events":
                events = _load_calendar()
                return {"events": events}
            elif action == "add_event":
                title = kwargs.get('title')
                if not title:
                    return {"error": "Missing 'title'"}
                date = kwargs.get('date', datetime.now().isoformat())
                description = kwargs.get('description', "")
                events = _load_calendar()
                event = {"id": len(events) + 1, "title": title, "date": date, "description": description}
                events.append(event)
                _save_calendar(events)
                return {"event": event, "message": "Event added"}
            elif action == "remove_event":
                event_id = kwargs.get('event_id') or kwargs.get('id')
                if event_id is None:
                    return {"error": "Missing 'event_id'"}
                events = _load_calendar()
                new_events = [e for e in events if e.get("id") != event_id]
                if len(new_events) == len(events):
                    return {"error": "Event not found"}
                _save_calendar(new_events)
                return {"message": "Event removed"}
            else:
                return {"error": f"Unknown action: {action}"}

        calendar_cap = CapabilityDefinition(
            name="calendar",
            description="Manage calendar events. Actions: 'list_events', 'add_event' (requires 'title', optional 'date', 'description'), 'remove_event' (requires 'event_id').",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action to perform", required=True, enum=["list_events", "add_event", "remove_event"]),
                CapabilityParameter(name="title", type="string", description="Event title (for add_event)", required=False),
                CapabilityParameter(name="date", type="string", description="Event date (ISO format, optional)", required=False),
                CapabilityParameter(name="description", type="string", description="Event description (optional)", required=False),
                CapabilityParameter(name="event_id", type="integer", description="Event ID (for remove_event)", required=False),
            ],
            handler=calendar_handler,
        )
        self.tool_registry.register(calendar_cap)

    def _register_email_tool(self):
        def email_handler(**kwargs):
            action = kwargs.get('action')
            if action != "send":
                return {"error": "Only 'send' action is supported"}
            to = kwargs.get('to') or kwargs.get('recipient')
            subject = kwargs.get('subject')
            body = kwargs.get('body') or kwargs.get('content')
            if not to or not subject or not body:
                return {"error": "Missing 'to', 'subject', or 'body'"}

            smtp_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("EMAIL_PORT", 587))
            smtp_user = os.getenv("EMAIL_USER", "")
            smtp_password = os.getenv("EMAIL_PASSWORD", "")

            if not smtp_user or not smtp_password:
                return {"error": "SMTP credentials not configured"}

            try:
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = to
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                return {"message": f"Email sent to {to}"}
            except Exception as e:
                return {"error": f"SMTP error: {str(e)}"}

        email_cap = CapabilityDefinition(
            name="email",
            description="Send emails. Action: 'send' (requires 'to', 'subject', 'body'). SMTP credentials must be set in environment variables.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: 'send'", required=True, enum=["send"]),
                CapabilityParameter(name="to", type="string", description="Recipient email address", required=True),
                CapabilityParameter(name="subject", type="string", description="Email subject", required=True),
                CapabilityParameter(name="body", type="string", description="Email body", required=True),
            ],
            handler=email_handler,
        )
        self.tool_registry.register(email_cap)

    def _register_email_reader_tool(self):
        def decode_email_header(header):
            if header is None:
                return ""
            decoded = decode_header(header)
            result = []
            for part, encoding in decoded:
                if isinstance(part, bytes):
                    try:
                        part = part.decode(encoding or 'utf-8', errors='ignore')
                    except:
                        part = part.decode('utf-8', errors='ignore')
                result.append(part)
            return ''.join(result)

        def get_email_body(msg):
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            return ""
                for part in msg.walk():
                    if part.get_content_type().startswith("text/"):
                        try:
                            return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            return ""
            else:
                try:
                    return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    return ""
            return ""

        def email_reader_handler(**kwargs):
            action = kwargs.get('action', 'list')
            imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
            imap_port = int(os.getenv("IMAP_PORT", 993))
            imap_user = os.getenv("EMAIL_USER", "")
            imap_password = os.getenv("EMAIL_PASSWORD", "")

            if not imap_user or not imap_password:
                return {"error": "IMAP credentials not configured. Please set EMAIL_USER and EMAIL_PASSWORD in .env"}

            try:
                conn = imaplib.IMAP4_SSL(imap_host, imap_port)
                conn.login(imap_user, imap_password)

                if action == "list":
                    conn.select("INBOX")
                    limit = kwargs.get('limit', 10)
                    status, data = conn.search(None, "ALL")
                    if status != "OK":
                        return {"error": "Failed to search emails"}
                    email_ids = data[0].split()
                    email_ids = email_ids[-limit:]

                    emails = []
                    for eid in reversed(email_ids):
                        status, msg_data = conn.fetch(eid, "(RFC822)")
                        if status != "OK":
                            continue
                        msg = email.message_from_bytes(msg_data[0][1])
                        subject = decode_email_header(msg.get("Subject", "No Subject"))
                        from_addr = decode_email_header(msg.get("From", "Unknown"))
                        date = msg.get("Date", "Unknown")
                        body = get_email_body(msg)[:500]
                        emails.append({
                            "id": eid.decode(),
                            "from": from_addr,
                            "subject": subject,
                            "date": date,
                            "body_preview": body[:200] + "..." if len(body) > 200 else body,
                        })
                    conn.close()
                    return {"emails": emails, "count": len(emails)}

                elif action == "read":
                    email_id = kwargs.get('email_id')
                    if not email_id:
                        return {"error": "Missing 'email_id' for read action"}
                    conn.select("INBOX")
                    status, msg_data = conn.fetch(email_id.encode(), "(RFC822)")
                    if status != "OK":
                        return {"error": f"Failed to fetch email {email_id}"}
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = decode_email_header(msg.get("Subject", "No Subject"))
                    from_addr = decode_email_header(msg.get("From", "Unknown"))
                    date = msg.get("Date", "Unknown")
                    body = get_email_body(msg)
                    conn.close()
                    return {
                        "id": email_id,
                        "from": from_addr,
                        "subject": subject,
                        "date": date,
                        "body": body,
                    }
                else:
                    return {"error": f"Unknown action: {action}"}
            except Exception as e:
                logger.error(f"IMAP error: {e}", exc_info=True)
                return {"error": f"IMAP error: {str(e)}"}

        email_reader_cap = CapabilityDefinition(
            name="email_reader",
            description="Read emails from your inbox. Actions: 'list' (list recent emails, optional 'limit' and 'days'), 'read' (read full email by 'email_id'). Requires IMAP credentials in .env.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: 'list' or 'read'", required=True, enum=["list", "read"]),
                CapabilityParameter(name="limit", type="integer", description="Number of emails to list (default 10)", required=False),
                CapabilityParameter(name="days", type="integer", description="Days to look back (default 7)", required=False),
                CapabilityParameter(name="email_id", type="string", description="Email ID to read (for 'read' action)", required=False),
            ],
            handler=email_reader_handler,
        )
        self.tool_registry.register(email_reader_cap)

    def _register_file_manager_tool(self):
        security_module = SecurityModule(secure_memory=self.secure_memory)
        synapse = SynapseInterface(security_module, secure_memory=self.secure_memory)

        def file_manager_handler(**kwargs):
            action = kwargs.get('action')
            # Accept both 'path' and 'directory'
            path = kwargs.get('path') or kwargs.get('directory')
            content = kwargs.get('content')

            if action == "list":
                if not path:
                    path = "."
                try:
                    import os
                    files = os.listdir(path)
                    return {"files": files}
                except Exception as e:
                    return {"error": str(e)}

            elif action == "read":
                if not path:
                    return {"error": "Missing 'path'"}
                result = synapse.read_file(path)
                if result is None:
                    return {"error": f"Could not read file {path}"}
                return {"content": result}

            elif action == "write":
                if not path or content is None:
                    return {"error": "Missing 'path' or 'content'"}
                success = synapse.write_file(path, content)
                if not success:
                    return {"error": f"Could not write to {path}"}
                return {"success": True}

            elif action == "delete":
                if not path:
                    return {"error": "Missing 'path'"}
                try:
                    os.remove(path)
                    return {"success": True}
                except Exception as e:
                    return {"error": str(e)}

            elif action == "mkdir":
                if not path:
                    return {"error": "Missing 'path'"}
                try:
                    os.makedirs(path, exist_ok=True)
                    return {"success": True}
                except Exception as e:
                    return {"error": str(e)}

            else:
                return {"error": f"Unknown action: {action}"}

        file_manager_cap = CapabilityDefinition(
            name="file_manager",
            description="Manage files and directories. Actions: 'list' (list directory contents), 'read' (read file), 'write' (write file), 'delete' (delete file), 'mkdir' (create directory). Requires 'path' for most actions.",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: 'list', 'read', 'write', 'delete', 'mkdir'", required=True, enum=["list", "read", "write", "delete", "mkdir"]),
                CapabilityParameter(name="path", type="string", description="File or directory path", required=False),
                CapabilityParameter(name="content", type="string", description="Content to write (for 'write' action)", required=False),
            ],
            handler=file_manager_handler,
        )
        self.tool_registry.register(file_manager_cap)

    def _register_github_tool(self):
        if not GITHUB_AVAILABLE:
            logging.warning("PyGithub not installed. GitHub capability will be disabled.")
            def github_handler(**kwargs):
                return {"error": "PyGithub not installed. Please install: pip install PyGithub"}
            github_cap = CapabilityDefinition(
                name="github",
                description="Interact with GitHub (placeholder – PyGithub not installed).",
                parameters=[
                    CapabilityParameter(name="action", type="string", description="Action", required=True),
                ],
                handler=github_handler,
            )
            self.tool_registry.register(github_cap)
            return

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logging.warning("GITHUB_TOKEN not set. GitHub capability will be limited.")

        def github_handler(**kwargs):
            action = kwargs.get('action')
            if not github_token:
                return {"error": "GITHUB_TOKEN not set in environment variables"}
            try:
                g = Github(github_token)
                if action == "list_repos":
                    repos = []
                    for repo in g.get_user().get_repos():
                        repos.append({"name": repo.name, "url": repo.html_url})
                    return {"repos": repos}
                elif action == "create_repo":
                    name = kwargs.get('name')
                    if not name:
                        return {"error": "Missing 'name'"}
                    description = kwargs.get('description', "")
                    private = kwargs.get('private', False)
                    repo = g.get_user().create_repo(name, description=description, private=private)
                    return {"repo": {"name": repo.name, "url": repo.html_url}}
                elif action == "get_file":
                    repo_name = kwargs.get('repo') or kwargs.get('repository')
                    path = kwargs.get('path')
                    if not repo_name or not path:
                        return {"error": "Missing 'repo' or 'path'"}
                    repo = g.get_repo(repo_name)
                    try:
                        contents = repo.get_contents(path)
                        return {"content": contents.decoded_content.decode()}
                    except GithubException as e:
                        if e.status == 404:
                            return {"error": "File not found"}
                        return {"error": str(e)}
                elif action == "create_issue":
                    repo_name = kwargs.get('repo') or kwargs.get('repository')
                    title = kwargs.get('title')
                    body = kwargs.get('body', "")
                    if not repo_name or not title:
                        return {"error": "Missing 'repo' or 'title'"}
                    repo = g.get_repo(repo_name)
                    issue = repo.create_issue(title=title, body=body)
                    return {"issue": {"number": issue.number, "url": issue.html_url}}
                elif action == "push":
                    repo_name = kwargs.get('repo') or kwargs.get('repository')
                    branch = kwargs.get('branch', "main")
                    commit_message = kwargs.get('message', "Automated commit via Jarvis")
                    files = kwargs.get('files', {})
                    if not repo_name:
                        return {"error": "Missing 'repo'"}
                    if not files:
                        return {"error": "No files to push"}
                    repo = g.get_repo(repo_name)
                    try:
                        ref = repo.get_git_ref(f"heads/{branch}")
                        latest_commit = repo.get_commit(ref.object.sha)
                        base_tree = latest_commit.commit.tree

                        changes = []
                        for file_path, content in files.items():
                            blob = repo.create_git_blob(content, "utf-8")
                            changes.append({
                                "path": file_path,
                                "mode": "100644",
                                "type": "blob",
                                "sha": blob.sha,
                            })
                        tree = repo.create_git_tree(changes, base_tree=base_tree)
                        parent = repo.get_git_commit(ref.object.sha)
                        commit = repo.create_git_commit(commit_message, tree, [parent])
                        ref.edit(commit.sha, force=True)
                        return {"success": True, "commit": commit.sha, "message": commit_message}
                    except GithubException as e:
                        return {"error": f"GitHub API error: {e.data.get('message', str(e))}"}
                else:
                    return {"error": f"Unknown action: {action}"}
            except GithubException as e:
                return {"error": f"GitHub API error: {e.data.get('message', str(e))}"}
            except Exception as e:
                return {"error": str(e)}

        github_cap = CapabilityDefinition(
            name="github",
            description="Interact with GitHub. Actions: 'list_repos', 'create_repo' (requires 'name'), 'get_file' (requires 'repo', 'path'), 'create_issue' (requires 'repo', 'title', optional 'body'), 'push' (requires 'repo', optional 'branch', 'message', 'files' - dictionary of file_path: content).",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action to perform", required=True, enum=["list_repos", "create_repo", "get_file", "create_issue", "push"]),
                CapabilityParameter(name="repo", type="string", description="Repository name (owner/repo)", required=False),
                CapabilityParameter(name="path", type="string", description="File path (for get_file)", required=False),
                CapabilityParameter(name="title", type="string", description="Issue title (for create_issue)", required=False),
                CapabilityParameter(name="body", type="string", description="Issue body (for create_issue)", required=False),
                CapabilityParameter(name="branch", type="string", description="Branch name (default 'main')", required=False),
                CapabilityParameter(name="message", type="string", description="Commit message (for push)", required=False),
                CapabilityParameter(name="files", type="object", description="Dictionary of file_path: new_content (for push)", required=False),
            ],
            handler=github_handler,
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
            description=(
                "Convert text to speech using Edge TTS. "
                "Provide 'text' (required), optional 'voice' (alloy/echo/fable/onyx/nova/shimmer), "
                "'response_format' (mp3/opus/aac/flac/wav/pcm), 'speed' (0.25-4.0), and 'output_path'."
            ),
            parameters=[
                CapabilityParameter(name="text", type="string", description="Text to speak", required=True),
                CapabilityParameter(name="voice", type="string", description="Voice: alloy, echo, fable, onyx, nova, shimmer", required=False),
                CapabilityParameter(name="response_format", type="string", description="Audio format (default mp3)", required=False),
                CapabilityParameter(name="speed", type="number", description="Speed 0.25-4.0 (default 1.0)", required=False),
                CapabilityParameter(name="output_path", type="string", description="Where to save the audio file", required=False),
            ],
            handler=tts_handler,
        )
        self.tool_registry.register(tts_cap)

    def _register_news_tool(self):
        def news_handler(**kwargs):
            topic = kwargs.get('topic', "technology")
            api_key = os.getenv("NEWS_API_KEY", "")
            if not api_key:
                return {"error": "NEWS_API_KEY not set in environment variables"}
            try:
                url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={api_key}&pageSize=5&sortBy=publishedAt"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    headlines = []
                    for article in articles[:5]:
                        headlines.append({
                            "title": article.get("title"),
                            "source": article.get("source", {}).get("name"),
                            "url": article.get("url"),
                        })
                    return {"articles": headlines}
                else:
                    return {"error": f"News API error: {response.status_code}"}
            except Exception as e:
                return {"error": str(e)}

        news_cap = CapabilityDefinition(
            name="news",
            description="Get the latest news headlines. Provide a 'topic' (e.g., technology, business, sports, science) – default is 'technology'.",
            parameters=[
                CapabilityParameter(name="topic", type="string", description="Topic to search for (e.g., technology, business, sports)", required=False),
            ],
            handler=news_handler,
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
                # Accept 'title' or 'task'
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
            description="Manage your todo list. Actions: 'list' (list all todos), 'add' (add a new todo, requires 'title'), 'complete' (mark a todo as complete, requires 'id'), 'delete' (delete a todo, requires 'id').",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: 'list', 'add', 'complete', 'delete'", required=True, enum=["list", "add", "complete", "delete"]),
                CapabilityParameter(name="title", type="string", description="Title of the todo (for 'add' action)", required=False),
                CapabilityParameter(name="id", type="integer", description="Todo ID (for 'complete' or 'delete')", required=False),
            ],
            handler=todo_handler,
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
            description="Manage notes. Actions: 'list' (list all notes), 'create' (create a new note, requires 'title' and 'content'), 'read' (read a note by 'id'), 'update' (update a note by 'id', optional 'title' or 'content'), 'delete' (delete a note by 'id').",
            parameters=[
                CapabilityParameter(name="action", type="string", description="Action: 'list', 'create', 'read', 'update', 'delete'", required=True, enum=["list", "create", "read", "update", "delete"]),
                CapabilityParameter(name="title", type="string", description="Title of the note", required=False),
                CapabilityParameter(name="content", type="string", description="Content of the note", required=False),
                CapabilityParameter(name="id", type="integer", description="Note ID", required=False),
            ],
            handler=notes_handler,
        )
        self.tool_registry.register(notes_cap)

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
