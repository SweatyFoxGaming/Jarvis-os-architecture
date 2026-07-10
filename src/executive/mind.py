import re
import json
import logging
import traceback
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard
from src.templates import PromptTemplate
from src.core.tools import ToolRegistry

try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None
try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.memory.tiered_memory import HierarchicalMemory

logger = logging.getLogger(__name__)

SEMANTIC_SEARCH_ENABLED = os.getenv("SEMANTIC_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
SEMANTIC_SEARCH_LIMIT = int(os.getenv("SEMANTIC_SEARCH_LIMIT", "5"))
MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "5"))


class ExecutiveMind(ICEO):
    def __init__(
        self,
        chief_of_staff: IChiefOfStaff,
        event_bus: IEventBus,
        digital_twin: DigitalTwin,
        engine=None,
        tool_registry: Optional[ToolRegistry] = None,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()
        self.engine = engine
        self.tool_registry = tool_registry
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner
        self.memory = HierarchicalMemory() if secure_memory is None else None
        self.active_goals: List[Goal] = []
        self._embedding_available = False

        if self._secure_memory and hasattr(self._secure_memory, 'search_semantic'):
            self._embedding_available = True
            logger.info("[ExecutiveMind] Semantic search available.")
        else:
            logger.warning("[ExecutiveMind] Semantic search not available; falling back to keyword.")

        logger.info(f"[ExecutiveMind] Initialized. SecureMemory: {secure_memory is not None}, "
                    f"Engine: {engine is not None and getattr(engine, 'llm', None) is not None}, "
                    f"ToolRegistry: {tool_registry is not None}, "
                    f"Semantic Search: {self._embedding_available}")

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        self._secure_memory = secure_memory
        self._embedding_available = hasattr(secure_memory, 'search_semantic')
        if self.memory is not None:
            self.memory = None
        logger.info("[ExecutiveMind] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        self._secure_runner = secure_runner
        logger.info("[ExecutiveMind] SecureCommandRunner attached.")

    def set_engine(self, engine):
        self.engine = engine
        logger.info("[ExecutiveMind] Engine attached.")

    def set_tool_registry(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        logger.info("[ExecutiveMind] ToolRegistry attached.")

    # ---------- Memory Helpers with user_id ----------
    def _get_recent_context(self, query: str = "", limit: int = 5, user_id: str = "default") -> str:
        if not self._secure_memory:
            if self.memory is not None:
                return self.memory.get_recent_context()
            return "No recent conversation history."

        if SEMANTIC_SEARCH_ENABLED and self._embedding_available and query:
            try:
                results = self._secure_memory.search_semantic(query, limit=SEMANTIC_SEARCH_LIMIT, user_id=user_id)
                if results:
                    context_lines = ["Relevant past conversations:"]
                    for r in results:
                        text = r.get("text", "")
                        if text.startswith("CONVERSATION: "):
                            text = text[13:]
                        context_lines.append(f"- {text}")
                    return "\n".join(context_lines)
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}. Falling back to recent.")

        try:
            results = self._secure_memory.search_by_text("", limit=limit, user_id=user_id)
            if results:
                context_lines = ["Recent conversation:"]
                for r in results:
                    text = r.get("text", "")
                    if text.startswith("CONVERSATION: "):
                        text = text[13:]
                    context_lines.append(f"- {text}")
                return "\n".join(context_lines)
        except Exception as e:
            logger.warning(f"Failed to retrieve recent context: {e}")

        return "No recent conversation history."

    def _store_conversation(self, user_input: str, response: str, user_id: str = "default"):
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"CONVERSATION: user: {user_input} | assistant: {response[:200]}",
                    metadata={
                        "type": "conversation",
                        "user_input": user_input,
                        "response_preview": response[:200],
                        "timestamp": datetime.now().isoformat(),
                    },
                    user_id=user_id,
                )
                logger.debug("[ExecutiveMind] Stored conversation in secure memory.")
            except Exception as e:
                logger.warning(f"Failed to store in secure memory: {e}")
        if self.memory is not None:
            try:
                self.memory.store_conversation(user_input, response)
            except Exception as e:
                logger.warning(f"Failed to store in legacy memory: {e}")

    # ---------- Tool Call Parsing ----------
    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        pattern = r'<tool_call\s+name="([^"]+)"\s+params=\'([^\']*)\'\s*/>'
        matches = re.findall(pattern, response)
        tool_calls = []
        for name, params_str in matches:
            try:
                params = json.loads(params_str) if params_str else {}
                tool_calls.append({"name": name, "params": params})
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool params: {params_str}")
        return tool_calls

    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.tool_registry:
            return {"error": "Tool registry not initialized"}
        results = {}
        for call in tool_calls:
            tool_name = call.get("name")
            params = call.get("params", {})
            result = self.tool_registry.execute_tool(tool_name, params)
            results[tool_name] = result
        return results

    # ---------- ReAct Loop ----------
    def _build_react_prompt(self, messages: List[Dict[str, str]], tools_desc: str) -> str:
        system_prompt = PromptTemplate.get_system_prompt()
        lines = [system_prompt]
        if tools_desc:
            lines.append("\n" + tools_desc)
            lines.append("\nIMPORTANT:")
            lines.append('- To use a tool, respond with:')
            lines.append('  <tool_call name="tool_name" params=\'{"param1": "value1"}\' />')
            lines.append("- You can use multiple tool calls in one response.")
            lines.append("- After receiving tool results, decide if you need more tools or can finalize.")
            lines.append("- To finalize, respond without a tool call.")
        lines.append("")
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"JARVIS: {content}")
            elif role == "tool_result":
                lines.append(f"Tool result: {content}")
            elif role == "system":
                lines.append(f"System: {content}")
            else:
                lines.append(f"{role}: {content}")
        lines.append("\nJARVIS:")
        return "\n".join(lines)

    def process_request(self, user_input: str, user_id: str = "default") -> str:
        logger.info(f"[ExecutiveMind] Processing for user {user_id}: {user_input[:80]}...")
        response = ""

        try:
            lower = user_input.lower().strip()
            # Fast Path: Direct commands (skip LLM)
            if any(g in lower for g in ["hello", "hi", "hey"]):
                response = "Hello! Good to see you again. What can I do for you?"
                self._store_conversation(user_input, response, user_id)
                return response
            if "how are you" in lower or "status" in lower:
                response = "I'm doing well, thanks for asking. Ready to help."
                self._store_conversation(user_input, response, user_id)
                return response
            if "time" in lower and len(user_input.split()) < 5:
                from datetime import datetime as dt
                response = f"The current time is {dt.now().strftime('%I:%M %p')}."
                self._store_conversation(user_input, response, user_id)
                return response

            # Main path: LLM with ReAct
            if self.engine is not None and getattr(self.engine, 'llm', None) is not None:
                context = self._get_recent_context(query=user_input, user_id=user_id)
                tools_desc = self.tool_registry.list_tools_for_prompt() if self.tool_registry else ""

                messages = [{"role": "user", "content": user_input}]
                if context and context != "No recent conversation history.":
                    messages.insert(0, {"role": "system", "content": f"Context:\n{context}"})

                final_answer = None
                raw_response = ""
                for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
                    logger.debug(f"[ExecutiveMind] ReAct iteration {iteration}/{MAX_TOOL_ITERATIONS}")
                    prompt = self._build_react_prompt(messages, tools_desc)
                    raw_response = self.engine.generate(prompt, max_tokens=1024, temperature=0.7)

                    tool_calls = self._parse_tool_calls(raw_response)
                    if not tool_calls:
                        final_answer = raw_response
                        break

                    logger.info(f"Iteration {iteration}: executing {len(tool_calls)} tool calls.")
                    tool_results = self._execute_tools(tool_calls)
                    messages.append({"role": "assistant", "content": raw_response})
                    for tool_name, result in tool_results.items():
                        result_text = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                        messages.append({
                            "role": "tool_result",
                            "content": f"Tool '{tool_name}' returned:\n{result_text}"
                        })

                if final_answer is None:
                    final_answer = raw_response if raw_response else "I'm sorry, I couldn't complete the task within the allowed steps."

                response = final_answer
            else:
                logger.info("[ExecutiveMind] No LLM available, using template.")
                context = self._get_recent_context(query=user_input, user_id=user_id)
                response = PromptTemplate.format(user_input, context)

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Unexpected error: {e}\n{error_trace}")
            response = "I'm sorry, an unexpected error occurred. Please check the logs."

        self._store_conversation(user_input, response, user_id)
        return response

    def assess_vision(self):
        logger.debug("assess_vision called (not implemented).")
        return "Executive Mind is operational."

    def shutdown(self):
        logger.info("[ExecutiveMind] Shutting down.")
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"Error closing secure memory: {e}")
        self._secure_memory = None
        self._secure_runner = None
