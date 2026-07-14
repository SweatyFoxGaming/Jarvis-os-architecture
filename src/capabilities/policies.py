from typing import List, Optional
from pydantic import BaseModel


class Permission(BaseModel):
    action: str
    resource: str
    conditions: Optional[dict] = None


class Policy(BaseModel):
    name: str
    permissions: List[Permission]
