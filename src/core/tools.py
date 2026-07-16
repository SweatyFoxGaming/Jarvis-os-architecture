"""
Unified Capability Registry – supports direct handler execution.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

from src.core.interfaces import IChiefOfStaff, IEventBus
from src.core.registry import CapabilityRegistry, DepartmentRegistry
from src.core.models import Task, Goal, Priority

logger = logging.getLogger(__name__)


class CapabilityParameter:
    """Parameter definition for a capability."""

    def __init__(
        self,
        name: str,
        type: str,
        description: str,
        required: bool = True,
        enum: Optional[List[str]] = None,
        default: Any = None,
    ):
        self.name = name
        self.type = type
        self.description = description
        self.required = required
        self.enum = enum
        self.default = default


class CapabilityDefinition:
    """Definition of a capability, including its handler."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: List[CapabilityParameter],
        handler: Optional[Callable] = None,
        department: str = "System",
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.department = department


class ToolRegistry:
    """
    Unified registry for capabilities/tools.
    Supports direct handler execution to bypass Task/Goal creation when needed.
    """

    def __init__(
        self,
        chief_of_staff: Optional[IChiefOfStaff] = None,
        cap_registry: Optional[CapabilityRegistry] = None,
        dept_registry: Optional[DepartmentRegistry] = None,
    ):
        self._capabilities: Dict[str, CapabilityDefinition] = {}
        self._chief_of_staff = chief_of_staff
        self._cap_registry = cap_registry
        self._dept_registry = dept_registry
        self._event_bus: Optional[IEventBus] = None
        logger.info("[CapabilityRegistry] Initialized.")

    def set_event_bus(self, event_bus: IEventBus):
        self._event_bus = event_bus
        logger.info("[CapabilityRegistry] EventBus attached.")

    def register(self, cap_def: CapabilityDefinition) -> None:
        """Register a capability definition."""
        self._capabilities[cap_def.name] = cap_def
        logger.info(f"[CapabilityRegistry] Registered capability: {cap_def.name}")

    def get(self, name: str) -> Optional[CapabilityDefinition]:
        """Retrieve a capability definition by name."""
        return self._capabilities.get(name)

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name.
        If the tool has a handler, call it directly (bypasses Task creation).
        Otherwise, create a Task and schedule it via ChiefOfStaff.
        """
        cap_def = self._capabilities.get(name)
        if not cap_def:
            return {"success": False, "error": f"Capability '{name}' not found"}

        # ---- DIRECT HANDLER PATH ----
        if cap_def.handler is not None:
            try:
                result = cap_def.handler(**params)
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"[CapabilityRegistry] Capability '{name}' handler failed: {e}")
                return {"success": False, "error": str(e)}

        # ---- FALLBACK: SCHEDULE VIA CHIEF OF STAFF (requires Goal) ----
        # This path is deprecated for direct execution but kept for legacy.
        if self._chief_of_staff is None:
            return {"success": False, "error": "ChiefOfStaff not available for scheduling"}

        try:
            # Create a temporary Goal (this is suboptimal – should use a real Goal)
            goal = Goal(
                title=f"Execute {name}",
                description=f"Execute tool {name} with parameters {params}",
                user_id="system",
            )
            task = Task(
                goal_uuid=goal.uuid,
                creator_id="system",
                target_capability=name,
                input_data=params,
            )
            # Schedule the task
            result = self._chief_of_staff.schedule_task(task, session_id=None)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"[CapabilityRegistry] Capability '{name}' scheduling failed: {e}")
            return {"success": False, "error": str(e)}

    def list_tools_for_prompt(self) -> str:
        """Generate a description of all registered tools for LLM prompting."""
        if not self._capabilities:
            return "No tools available."

        lines = ["## Available Tools\n"]
        for name, cap_def in self._capabilities.items():
            lines.append(f"### {name}")
            lines.append(f"Description: {cap_def.description}")
            if cap_def.parameters:
                lines.append("Parameters:")
                for p in cap_def.parameters:
                    required = "required" if p.required else "optional"
                    enum_str = f" (options: {', '.join(p.enum)})" if p.enum else ""
                    lines.append(f"  - {p.name} ({p.type}) {required}{enum_str}: {p.description}")
            else:
                lines.append("Parameters: None")
            lines.append("")
        return "\n".join(lines)

    def shutdown(self):
        """Clean up resources."""
        logger.info("[CapabilityRegistry] Shutting down.")
