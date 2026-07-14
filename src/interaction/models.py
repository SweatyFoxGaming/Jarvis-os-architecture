"""
Interaction Platform – Core Models
Governed by INTERACTION_MODEL.md
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field


# ---------- Enums ----------

class InteractionSource(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TERMINAL = "terminal"
    VOICE = "voice"
    API = "api"
    NOTIFICATION = "notification"


class InteractionKind(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    FILE = "file"
    IMAGE = "image"
    VIDEO = "video"
    COMMAND = "command"
    EVENT = "event"


class SessionState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Tone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    BRIEF = "brief"
    TECHNICAL = "technical"
    ENCOURAGING = "encouraging"
    DIRECT = "direct"
    EMPATHETIC = "empathetic"


class NotificationType(str, Enum):
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    APPROVAL_REQUIRED = "approval_required"
    REMINDER = "reminder"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    INSIGHT = "insight"
    CONVERSATION = "conversation"


# ---------- Core Models ----------

class Interaction(BaseModel):
    """An atomic unit of user input."""
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    source: InteractionSource
    kind: InteractionKind
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "forbid"


class Message(BaseModel):
    """A single message in a conversation."""
    id: UUID = Field(default_factory=uuid4)
    role: MessageRole
    content: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "forbid"


class Session(BaseModel):
    """Persistent context for a user's interaction."""
    session_id: UUID = Field(default_factory=uuid4)
    user_id: str
    state: SessionState = SessionState.IDLE
    conversation: List[Message] = Field(default_factory=list)
    active_goal_uuid: Optional[UUID] = None
    workspace: Dict[str, Any] = Field(default_factory=dict)
    pending_confirmations: List[Dict[str, Any]] = Field(default_factory=list)
    tone: Tone = Tone.PROFESSIONAL
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    class Config:
        extra = "forbid"


class InteractionResponse(BaseModel):
    """Presentation-independent response."""
    text: Optional[str] = None
    markdown: Optional[str] = None
    audio: Optional[bytes] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    notifications: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    trace: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = "forbid"


class Notification(BaseModel):
    """Proactive message sent to the user."""
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    type: NotificationType
    title: str
    body: str
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    priority: int = Field(default=1, ge=0, le=3)  # 0=low, 1=medium, 2=high, 3=urgent
    read: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "forbid"
