from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Prompt(BaseModel):
    id:         str = Field(default_factory=lambda: str(uuid.uuid4()))
    text:       str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AgentStatus(BaseModel):
    connected: bool
    last_seen: Optional[str] = None
    clients:   int = 0
