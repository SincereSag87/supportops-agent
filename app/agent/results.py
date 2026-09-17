from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.decisions import AgentDecision
from app.agent.models import AgentStatus
from app.policies.models import ApprovalRequest
from app.tools.models import ToolCall, ToolResult


class AgentResult(BaseModel):
    request_id: UUID
    status: AgentStatus
    response: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    decision_history: list[AgentDecision] = Field(default_factory=list)
    approvals_required: list[ApprovalRequest] = Field(default_factory=list)
    escalated: bool = False
    error: str | None = None
