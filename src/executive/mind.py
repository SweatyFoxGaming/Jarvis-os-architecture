import re
import json
import logging
import traceback
import os
from typing import List, Dict, Any, Optional, Tuple
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
SEMANTIC_SEARCH_LIMIT = int(os.getenv("SEMANTIC_SEARCH_LIMIT", "2"))
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

    def _get_recent_context(self, query: str = "", limit: int = 1, user_id: str = "default") -> str:
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
                    context = "\n".join(context_lines)
                    if len(context) > 300:
                        context = context[:300] + "..."
                    return context
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
                context = "\n".join(context_lines)
                if len(context) > 300:
                    context = context[:300] + "..."
                return context
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

    # ---------- Main Process Request with Trace ----------
    def process_request(self, user_input: str, user_id: str = "default", collect_trace: bool = True, force_agent: bool = False) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        trace = [] if collect_trace else None
        logger.info(f"[ExecutiveMind] Processing for user {user_id}: {user_input[:80]}...")

        def add_trace(step: str, message: str, data: dict = None):
            if trace is not None:
                trace.append({
                    "step": step,
                    "message": message,
                    "data": data or {},
                    "timestamp": datetime.now().isoformat()
                })

        response = ""
        try:
            lower = user_input.lower().strip()

            # ---- Fast Path: greetings (only if NOT forced) ----
            if not force_agent:
                if any(g in lower for g in ["hello", "hi", "hey"]):
                    response = "Hello! Good to see you again. What can I do for you?"
                    add_trace("fast_path", "Direct greeting response", {"greeting": True})
                    self._store_conversation(user_input, response, user_id)
                    return response, trace

                if "how are you" in lower or "status" in lower:
                    response = "I'm doing well, thanks for asking. Ready to help."
                    add_trace("fast_path", "Status response", {"status": "ok"})
                    self._store_conversation(user_input, response, user_id)
                    return response, trace

                if "time" in lower and len(user_input.split()) < 5:
                    from datetime import datetime as dt
                    response = f"The current time is {dt.now().strftime('%I:%M %p')}."
                    add_trace("fast_path", "Time response", {"time": response})
                    self._store_conversation(user_input, response, user_id)
                    return response, trace

            # ---- DIRECT EXECUTION: execute: ... ----
            if "execute:" in lower or "system_control" in lower:
                import re
                cmd_match = re.search(r'(?:execute|system_control)[\s:]+(.+)', user_input, re.IGNORECASE)
                if cmd_match:
                    command = cmd_match.group(1).strip()
                    if self.tool_registry:
                        result = self.tool_registry.execute_tool("system_control", {"action": "execute", "command": command})
                        if result.get("success"):
                            output = result.get('result', {}).get('output', '')
                            response = f"✅ Command executed.\nOutput:\n{output}"
                        else:
                            response = f"❌ Command failed.\nError: {result.get('error', 'Unknown error')}"
                        add_trace("direct_execution", "Direct system_control execution", {"command": command})
                        self._store_conversation(user_input, response, user_id)
                        return response, trace
                    else:
                        response = "Tool registry not available."
                        add_trace("error", "Tool registry missing", {})
                        self._store_conversation(user_input, response, user_id)
                        return response, trace

            # ---- Main path: LLM with ReAct (only if engine is available) ----
            if self.engine is not None and getattr(self.engine, 'llm', None) is not None:
                context = self._get_recent_context(query=user_input, limit=2, user_id=user_id)
                tools_desc = self.tool_registry.list_tools_for_prompt() if self.tool_registry else ""

                messages = [{"role": "user", "content": user_input}]
                if context and context != "No recent conversation history.":
                    messages.insert(0, {"role": "system", "content": f"Context:\n{context}"})
                    add_trace("context_retrieval", "Retrieved recent context", {"context": context[:200]})

                final_answer = None
                raw_response = ""
                for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
                    add_trace("react_iteration", f"Iteration {iteration}/{MAX_TOOL_ITERATIONS}", {"iteration": iteration})

                    prompt = self._build_react_prompt(messages, tools_desc)
                    try:
                        raw_response = self.engine.generate(prompt, max_tokens=512, temperature=0.7)
                    except Exception as e:
                        if "context window" in str(e).lower() or "tokens" in str(e).lower():
                            logger.warning(f"Token limit exceeded in iteration {iteration}: {e}")
                            response = "I'm sorry, the conversation is too long. Let's start fresh or shorten your request."
                            add_trace("error", "Token limit exceeded", {"error": str(e)})
                            self._store_conversation(user_input, response, user_id)
                            return response, trace
                        else:
                            raise

                    add_trace("llm_response", f"LLM generated response (iteration {iteration})", {"response_preview": raw_response[:200]})

                    tool_calls = self._parse_tool_calls(raw_response)
                    if not tool_calls:
                        final_answer = raw_response
                        add_trace("finalize", "No tool calls, finalizing", {})
                        break

                    add_trace("tool_calls", f"Executing {len(tool_calls)} tool calls", {"tools": [t["name"] for t in tool_calls]})
                    tool_results = self._execute_tools(tool_calls)
                    for tool_name, result in tool_results.items():
                        add_trace("tool_result", f"Tool '{tool_name}' completed", {"result_preview": str(result)[:200]})

                    messages.append({"role": "assistant", "content": raw_response})
                    for tool_name, result in tool_results.items():
                        result_text = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                        messages.append({
                            "role": "tool_result",
                            "content": f"Tool '{tool_name}' returned:\n{result_text}"
                        })

                if final_answer is None:
                    final_answer = raw_response if raw_response else "I'm sorry, I couldn't complete the task within the allowed steps."
                    add_trace("fallback", "Used fallback after iteration limit", {})

                response = final_answer
                add_trace("synthesis", "Final response synthesized", {"response_preview": response[:200]})

            else:
                # No LLM: fallback to template
                logger.info("[ExecutiveMind] No LLM available, using template.")
                context = self._get_recent_context(query=user_input, limit=2, user_id=user_id)
                response = PromptTemplate.format(user_input, context)
                add_trace("template_fallback", "Used template response (no LLM)", {})

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Unexpected error: {e}\n{error_trace}")
            response = "I'm sorry, an unexpected error occurred. Please check the logs."
            add_trace("error", f"Unexpected error: {str(e)}", {"error": str(e)})

        self._store_conversation(user_input, response, user_id)
        return response, trace

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
