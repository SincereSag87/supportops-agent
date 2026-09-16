from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentMessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"


class AgentMessage(BaseModel):
    role: AgentMessageRole
    content: str
    timestamp: datetime | None = Field(default_factory=lambda: datetime.now(UTC))


class AgentRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    user_input: str
    customer_id: str | None = None
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)


class AgentStatus(StrEnum):
    RECEIVED = "received"
    REASONING = "reasoning"
    AWAITING_TOOL = "awaiting_tool"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"
