# src/core/tools.py
import json
import time
import logging
from typing import Dict, Any, List, Callable, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CapabilityParameter(BaseModel):
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type: string, integer, boolean, object")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(False, description="Whether this parameter is required")
    enum: Optional[List[str]] = Field(None, description="Allowed values (if applicable)")


class CapabilityDefinition(BaseModel):
    name: str = Field(..., description="Unique capability name")
    description: str = Field(..., description="What this capability does")
    parameters: List[CapabilityParameter] = Field(default_factory=list)
    handler: Optional[Callable] = Field(None, description="Function to execute this capability")
    department: Optional[str] = Field(None, description="Department that owns this capability (legacy)")

    class Config:
        extra = "forbid"


class CapabilityRegistry:
    def __init__(self, chief_of_staff=None, cap_registry=None, dept_registry=None):
        self._capabilities: Dict[str, CapabilityDefinition] = {}
        self._chief_of_staff = chief_of_staff
        self._cap_registry = cap_registry
        self._dept_registry = dept_registry
        self._task_results: Dict[str, Any] = {}
        self._event_bus = None
        logger.info("[CapabilityRegistry] Initialized.")

    def set_chief_of_staff(self, chief_of_staff):
        self._chief_of_staff = chief_of_staff
        logger.info("[CapabilityRegistry] Chief of Staff attached.")

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus
        if event_bus:
            event_bus.subscribe("TaskCompleted", self._on_task_completed)
            event_bus.subscribe("TaskFailed", self._on_task_failed)
        logger.info("[CapabilityRegistry] EventBus attached.")

    def set_secure_memory(self, secure_memory):
        pass  # stub

    def _on_task_completed(self, event):
        task_id = event.payload.get("task_id")
        if task_id:
            self._task_results[task_id] = {"status": "completed", "data": event.payload.get("output_data", {})}
            logger.debug(f"[CapabilityRegistry] Task {task_id} completed.")

    def _on_task_failed(self, event):
        task_id = event.payload.get("task_id")
        if task_id:
            self._task_results[task_id] = {"status": "failed", "error": event.payload.get("reason", "Unknown error")}
            logger.warning(f"[CapabilityRegistry] Task {task_id} failed.")

    def register(self, capability: CapabilityDefinition, department: Optional[str] = None) -> None:
        if department:
            capability.department = department
        if capability.name in self._capabilities:
            logger.warning(f"[CapabilityRegistry] Capability '{capability.name}' already registered. Overwriting.")
        self._capabilities[capability.name] = capability
        logger.info(f"[CapabilityRegistry] Registered capability: {capability.name}")

    def register_tool(self, tool: CapabilityDefinition) -> None:
        self.register(tool)

    def get(self, name: str) -> Optional[CapabilityDefinition]:
        return self._capabilities.get(name)

    def get_tool(self, name: str) -> Optional[CapabilityDefinition]:
        return self.get(name)

    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": c.name,
                "description": c.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "enum": p.enum,
                    }
                    for p in c.parameters
                ],
            }
            for c in self._capabilities.values()
        ]

    def list_tools(self) -> List[Dict[str, Any]]:
        return self.list()

    def list_for_prompt(self) -> str:
        if not self._capabilities:
            return "No capabilities available."
        lines = ["Capabilities (use only if needed):"]
        for cap in self._capabilities.values():
            desc = cap.description.split('.')[0] if cap.description else ""
            lines.append(f"- {cap.name}: {desc}")
        return "\n".join(lines)

    def list_tools_for_prompt(self) -> str:
        return self.list_for_prompt()

    def execute(self, capability_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        goal_uuid = params.pop("_goal_uuid", None)
        capability = self.get(capability_name)
        if capability is None:
            return {"success": False, "error": f"Capability '{capability_name}' not found"}

        if capability.handler:
            try:
                result = capability.handler(**params)
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"[CapabilityRegistry] Capability '{capability_name}' handler failed: {e}")
                return {"success": False, "error": str(e)}

        if self._chief_of_staff and capability.department:
            try:
                from src.core.models import Task, ExecutionState
                task = Task(
                    creator_id="CapabilityRegistry",
                    target_capability=capability_name,
                    input_data=params,
                    goal_uuid=goal_uuid,
                    state=ExecutionState.CREATED,
                )
                self._chief_of_staff.schedule_task(task)
                task_id = str(task.uuid)
                logger.info(f"[CapabilityRegistry] Scheduled task {task_id} for capability '{capability_name}' (goal: {goal_uuid})")
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
                logger.error(f"[CapabilityRegistry] Capability '{capability_name}' scheduling failed: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "No handler or department defined for this capability"}

    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(tool_name, params)

    def shutdown(self):
        logger.info("[CapabilityRegistry] Shutting down.")
        self._capabilities.clear()
        self._task_results.clear()
        if self._event_bus:
            try:
                self._event_bus.unsubscribe("TaskCompleted", self._on_task_completed)
                self._event_bus.unsubscribe("TaskFailed", self._on_task_failed)
            except Exception:
                pass


# ---------- Backward Compatibility Aliases ----------
ToolRegistry = CapabilityRegistry
ToolDefinition = CapabilityDefinition
ToolParameter = CapabilityParameter
