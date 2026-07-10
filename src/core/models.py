from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator, confloat, conint, constr

# ---------- Enums ----------
class TaskStatus(str, Enum):
    """Status of a task throughout its lifecycle."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        """Return True if the status is terminal (completed, failed, cancelled)."""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def is_active(self) -> bool:
        """Return True if the task is still in progress (pending, assigned, in_progress)."""
        return self in (TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS)


class Priority(int, Enum):
    """Priority levels for tasks and goals."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3

    def __str__(self) -> str:
        return self.name


class RiskLevel(int, Enum):
    """Risk assessment levels."""
    NEGLIGIBLE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def is_acceptable(self) -> bool:
        """Return True if risk level is MEDIUM or lower."""
        return self <= RiskLevel.MEDIUM


# ---------- Pydantic Models ----------
class ResourceBudget(BaseModel):
    """Resource limits for a task."""
    cpu_limit: float = Field(default=1.0, ge=0.0, le=100.0, description="CPU limit in percentage or units")
    ram_limit_mb: int = Field(default=256, ge=0, description="RAM limit in MB")
    token_limit: int = Field(default=2048, ge=0, description="Maximum tokens allowed")
    time_limit_sec: int = Field(default=60, ge=0, description="Time limit in seconds")

    class Config:
        extra = "forbid"


class Goal(BaseModel):
    """Represents a high-level objective."""
    uuid: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    status: TaskStatus = TaskStatus.PENDING
    parent_goal: Optional[UUID] = None
    priority: Priority = Priority.MEDIUM
    deadline: Optional[datetime] = None
    alignment: str = Field(default="Strategic", max_length=100)

    class Config:
        extra = "forbid"


class ExecutiveDecision(BaseModel):
    """Represents a strategic decision made by the CEO or Executive Mind."""
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    intent: str = Field(..., min_length=1, max_length=500)
    context: str = Field(..., max_length=2000)
    goals: List[UUID] = Field(default_factory=list)
    selected_capabilities: List[str] = Field(default_factory=list)
    reasoning_summary: str = Field(..., max_length=2000)
    confidence: float = Field(..., ge=0.0, le=1.0)
    expected_outcome: str = Field(..., max_length=1000)
    estimated_cost: float = Field(..., ge=0.0)
    estimated_time_sec: int = Field(..., ge=0)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    approved: bool = False

    class Config:
        extra = "forbid"


class Capability(BaseModel):
    """Defines a capability that can be performed by a department."""
    name: str = Field(..., min_length=1, max_length=100)
    purpose: str = Field(..., max_length=500)
    inputs: Dict[str, str] = Field(default_factory=dict)
    outputs: Dict[str, str] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    estimated_cost: float = Field(default=0.0, ge=0.0)
    estimated_time_sec: int = Field(default=0, ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    required_resources: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"


class Task(BaseModel):
    """Represents a unit of work assigned to a department."""
    uuid: UUID = Field(default_factory=uuid4)
    creator_id: str = Field(..., min_length=1, max_length=100)
    target_capability: str = Field(..., min_length=1, max_length=100)
    assigned_department_id: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    dependencies: List[UUID] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def add_history_entry(self, entry: Dict[str, Any]) -> None:
        """Append a history entry with a timestamp."""
        entry.setdefault("timestamp", datetime.now().isoformat())
        self.history.append(entry)

    def mark_completed(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark the task as completed and store output data."""
        self.status = TaskStatus.COMPLETED
        self.progress = 1.0
        if output_data is not None:
            self.output_data = output_data
        self.add_history_entry({"event": "completed"})

    def mark_failed(self, error_message: str) -> None:
        """Mark the task as failed with an error message."""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.add_history_entry({"event": "failed", "error": error_message})

    def mark_cancelled(self) -> None:
        """Mark the task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.add_history_entry({"event": "cancelled"})

    def update_progress(self, progress: float) -> None:
        """Update progress (0.0 to 1.0) and log the change."""
        if not (0.0 <= progress <= 1.0):
            raise ValueError("Progress must be between 0.0 and 1.0")
        self.progress = progress
        self.add_history_entry({"event": "progress_update", "progress": progress})

    class Config:
        extra = "forbid"


class Event(BaseModel):
    """Event on the internal event bus."""
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str = Field(..., min_length=1, max_length=100)
    source: str = Field(..., min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)

    class Config:
        extra = "forbid"


class MemoryRecord(BaseModel):
    """A record stored in memory (episodic or semantic)."""
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = Field(..., min_length=1, max_length=100)
    content: Any  # Can be any JSON-serializable object
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    verification_status: str = Field(default="unverified", max_length=50)
    embedding: Optional[List[float]] = None
    tags: List[str] = Field(default_factory=list)
    usage_count: int = Field(default=0, ge=0)
    last_accessed: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        """Update last_accessed and increment usage_count."""
        self.last_accessed = datetime.now()
        self.usage_count += 1

    class Config:
        extra = "forbid"
