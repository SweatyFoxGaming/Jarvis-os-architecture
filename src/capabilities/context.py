from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from uuid import UUID

from src.core.models import Goal, Task, MemoryRecord
from src.capabilities.budgets import CapabilityBudget


class ExecutionContext(BaseModel):
    """
    Everything a capability needs to know about the current execution.
    """
    goal: Goal
    task: Task
    user_id: str
    budget: CapabilityBudget
    execution_id: str = Field(default_factory=lambda: str(UUID))
    logger: Optional[Any] = None
    cancellation_token: Optional[Any] = None
    event_publisher: Optional[Any] = None
    memory: Optional[Any] = None
    policies: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
