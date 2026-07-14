from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator, confloat, conint, constr

# ---------- Enums ----------

# Formal Execution State Machine
class ExecutionState(str, Enum):
    """Universal execution lifecycle for all tasks and goals."""
    CREATED = "created"
    ACCEPTED = "accepted"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    RETRYING = "retrying"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    def is_terminal(self) -> bool:
        return self in (ExecutionState.COMPLETED, ExecutionState.ARCHIVED)

    def is_active(self) -> bool:
        return self in (
            ExecutionState.CREATED,
            ExecutionState.ACCEPTED,
            ExecutionState.PLANNED,
            ExecutionState.READY,
            ExecutionState.RUNNING,
            ExecutionState.WAITING,
            ExecutionState.RETRYING,
            ExecutionState.REVIEWING,
        )


class PlatformState(str, Enum):
    """Explicit platform lifecycle states."""
    BOOTING = "booting"
    LOADING = "loading"
    READY = "ready"
    WORKING = "working"
    LEARNING = "learning"
    SLEEPING = "sleeping"
    RECOVERING = "recovering"
    UPDATING = "updating"
    SHUTDOWN = "shutdown"


class Priority(int, Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3


class RiskLevel(int, Enum):
    NEGLIGIBLE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ---------- Budgets ----------

class GoalBudget(BaseModel):
    """Architectural budget for a Goal."""
    time_budget_sec: int = Field(default=300, ge=0)
    token_budget: int = Field(default=4096, ge=0)
    priority: Priority = Priority.MEDIUM
    deadline: Optional[datetime] = None
    max_retries: int = Field(default=3, ge=0)
    max_parallel_tasks: int = Field(default=5, ge=1)
    quality_target: float = Field(default=0.8, ge=0.0, le=1.0)

    class Config:
        extra = "forbid"


class ResourceBudget(BaseModel):
    """Resource limits for a task."""
    cpu_limit: float = Field(default=1.0, ge=0.0, le=100.0)
    ram_limit_mb: int = Field(default=256, ge=0)
    token_limit: int = Field(default=2048, ge=0)
    time_limit_sec: int = Field(default=60, ge=0)

    class Config:
        extra = "forbid"


# ---------- Goal (Primary Domain Object) ----------

class Goal(BaseModel):
    """A Goal represents the user's intent. Everything derives from this."""
    uuid: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    state: ExecutionState = ExecutionState.CREATED
    parent_goal: Optional[UUID] = None
    budget: GoalBudget = Field(default_factory=GoalBudget)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    user_id: str = Field(default="default", max_length=100)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result_summary: Optional[str] = None
    error_message: Optional[str] = None

    def transition_to(self, new_state: ExecutionState) -> None:
        """Move the goal to a new state with validation."""
        self.state = new_state
        self.updated_at = datetime.now()
        if new_state == ExecutionState.COMPLETED:
            self.completed_at = datetime.now()

    class Config:
        extra = "forbid"


# ---------- Task (Derived from Goal) ----------

class Task(BaseModel):
    """A Task is a unit of work belonging to a Goal."""
    uuid: UUID = Field(default_factory=uuid4)
    goal_uuid: UUID = Field(..., description="The Goal this task belongs to")
    creator_id: str = Field(..., min_length=1, max_length=100)
    target_capability: str = Field(..., min_length=1, max_length=100)
    assigned_worker_id: Optional[str] = None
    state: ExecutionState = ExecutionState.CREATED
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    dependencies: List[UUID] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def transition_to(self, new_state: ExecutionState) -> None:
        self.state = new_state
        self.updated_at = datetime.now()
        if new_state == ExecutionState.COMPLETED:
            self.completed_at = datetime.now()

    def add_history_entry(self, entry: Dict[str, Any]) -> None:
        entry.setdefault("timestamp", datetime.now().isoformat())
        self.history.append(entry)

    class Config:
        extra = "forbid"


# ---------- Capability (First-Class Object) ----------

class Capability(BaseModel):
    """A Capability represents an executable ability of the platform."""
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(default="1.0.0", max_length=20)
    purpose: str = Field(..., max_length=500)
    inputs: Dict[str, str] = Field(default_factory=dict)
    outputs: Dict[str, str] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    estimated_cost: float = Field(default=0.0, ge=0.0)
    estimated_time_sec: int = Field(default=0, ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    required_resources: Dict[str, Any] = Field(default_factory=dict)
    health_status: str = Field(default="healthy", max_length=50)
    owner: str = Field(default="system", max_length=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "forbid"


# ---------- Memory Lifecycle ----------

class MemoryStage(str, Enum):
    """Formal memory pipeline stages."""
    CONVERSATION = "conversation"
    WORKING = "working"
    EPISODE = "episode"
    REVIEW = "review"
    CONSOLIDATION = "consolidation"
    SEMANTIC = "semantic"
    ARCHIVE = "archive"


class MemoryRecord(BaseModel):
    """A record stored in memory with explicit stage."""
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = Field(..., min_length=1, max_length=100)
    content: Any
    stage: MemoryStage = MemoryStage.CONVERSATION
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    verification_status: str = Field(default="unverified", max_length=50)
    embedding: Optional[List[float]] = None
    tags: List[str] = Field(default_factory=list)
    usage_count: int = Field(default=0, ge=0)
    last_accessed: datetime = Field(default_factory=datetime.now)
    goal_uuid: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def advance_stage(self, next_stage: MemoryStage) -> None:
        self.stage = next_stage
        self.timestamp = datetime.now()

    def touch(self) -> None:
        self.last_accessed = datetime.now()
        self.usage_count += 1

    class Config:
        extra = "forbid"


# ---------- Events (Standard Vocabulary) ----------

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


# ---------- Executive Decision ----------

class ExecutiveDecision(BaseModel):
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
