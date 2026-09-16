from pydantic import BaseModel, Field

from app.agent.models import AgentMessage, AgentRequest, AgentStatus
from app.policies.models import ProposedAction


class AgentState(BaseModel):
    request: AgentRequest
    status: AgentStatus = AgentStatus.RECEIVED
    messages: list[AgentMessage] = Field(default_factory=list)
    step_count: int = 0
    pending_action: ProposedAction | None = None
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
