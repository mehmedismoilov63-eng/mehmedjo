from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field


class Prompt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = "claude"
    text: str
    status: str = "queued"
    result: Optional[str] = None
    action: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    user: Optional[dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class AgentStatus(BaseModel):
    connected: bool
    last_seen: Optional[str] = None
    clients: int = 0
    system: Optional[dict[str, Any]] = None
