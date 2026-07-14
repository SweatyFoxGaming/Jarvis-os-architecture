from typing import Optional
from pydantic import BaseModel, Field


class CapabilityBudget(BaseModel):
    time_sec: int = Field(ge=0, default=30)
    token_limit: int = Field(ge=0, default=4096)
    memory_mb: int = Field(ge=0, default=256)
    max_retries: int = Field(ge=0, default=3)
    priority: int = Field(ge=0, le=3, default=1)
