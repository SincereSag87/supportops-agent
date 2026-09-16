from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.models import AgentStatus
from app.policies.models import ApprovalRequest
from app.tools.models import ToolCall


class AgentResult(BaseModel):
    request_id: UUID
    status: AgentStatus
    response: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    approvals_required: list[ApprovalRequest] = Field(default_factory=list)
    escalated: bool = False
    error: str | None = None
