# src/core/tools.py
import json
import time
import logging
from typing import Dict, Any, List, Callable, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type: string, integer, boolean, object")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(False, description="Whether this parameter is required")
    enum: Optional[List[str]] = Field(None, description="Allowed values (if applicable)")


class ToolDefinition(BaseModel):
    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="What this tool does")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    handler: Optional[Callable] = Field(None, description="Function to execute this tool")
    department: Optional[str] = Field(None, description="Department that handles this tool")


class ToolRegistry:
    """
    Registry for all tools available to the LLM.
    """

    def __init__(self, chief_of_staff=None, cap_registry=None, dept_registry=None):
        self._tools: Dict[str, ToolDefinition] = {}
        self._chief_of_staff = chief_of_staff
        self._cap_registry = cap_registry
        self._dept_registry = dept_registry
        self._task_results: Dict[str, Any] = {}
        self._event_bus = None
        logger.info("[ToolRegistry] Initialized.")

    def set_chief_of_staff(self, chief_of_staff):
        self._chief_of_staff = chief_of_staff
        logger.info("[ToolRegistry] Chief of Staff attached.")

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus
        if event_bus:
            event_bus.subscribe("TaskCompleted", self._on_task_completed)
            event_bus.subscribe("TaskFailed", self._on_task_failed)
        logger.info("[ToolRegistry] EventBus attached.")

    def _on_task_completed(self, event):
        task_id = event.payload.get("task_id")
        if task_id:
            self._task_results[task_id] = {"status": "completed", "data": event.payload.get("output_data", {})}
            logger.debug(f"[ToolRegistry] Task {task_id} completed.")

    def _on_task_failed(self, event):
        task_id = event.payload.get("task_id")
        if task_id:
            self._task_results[task_id] = {"status": "failed", "error": event.payload.get("reason", "Unknown error")}
            logger.warning(f"[ToolRegistry] Task {task_id} failed.")

    def register_tool(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            logger.warning(f"[ToolRegistry] Tool '{tool.name}' already registered. Overwriting.")
        self._tools[tool.name] = tool
        logger.info(f"[ToolRegistry] Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "enum": p.enum,
                    }
                    for p in t.parameters
                ],
            }
            for t in self._tools.values()
        ]

    def list_tools_for_prompt(self) -> str:
        """Generate a compact tool description list for the LLM prompt."""
        if not self._tools:
            return "No tools available."

        lines = ["Tools (use only if needed):"]
        for tool in self._tools.values():
            # Short description – first sentence only
            desc = tool.description.split('.')[0] if tool.description else ""
            lines.append(f"- {tool.name}: {desc}")
        return "\n".join(lines)

    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.get_tool(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        if tool.handler:
            try:
                result = tool.handler(**params)
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"[ToolRegistry] Tool '{tool_name}' handler failed: {e}")
                return {"success": False, "error": str(e)}

        if self._chief_of_staff and tool.department:
            try:
                from src.core.models import Task, Priority
                task = Task(
                    creator_id="ToolRegistry",
                    target_capability=tool_name,
                    priority=Priority.MEDIUM,
                    input_data=params,
                )
                self._chief_of_staff.schedule_task(task)
                task_id = str(task.uuid)
                logger.info(f"[ToolRegistry] Scheduled task {task_id} for tool '{tool_name}'")
                timeout = 60
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if task_id in self._task_results:
                        result = self._task_results.pop(task_id)
                        if result.get("status") == "completed":
                            return {"success": True, "result": result.get("data", {})}
                        else:
                            return {"success": False, "error": result.get("error", "Task failed")}
                    if task_id in self._chief_of_staff.active_tasks:
                        time.sleep(0.5)
                        continue
                    break
                return {"success": False, "error": f"Task {task_id} timed out after {timeout}s"}
            except Exception as e:
                logger.error(f"[ToolRegistry] Tool '{tool_name}' scheduling failed: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "No handler or department defined for this tool"}

    def shutdown(self):
        logger.info("[ToolRegistry] Shutting down.")
        self._tools.clear()
        self._task_results.clear()
        if self._event_bus:
            try:
                self._event_bus.unsubscribe("TaskCompleted", self._on_task_completed)
                self._event_bus.unsubscribe("TaskFailed", self._on_task_failed)
            except Exception:
                pass
