from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AgentDecisionType(StrEnum):
    TOOL_CALL = "tool_call"
    FINAL_RESPONSE = "final_response"
    ESCALATE = "escalate"
    FAIL = "fail"


class AgentDecision(BaseModel):
    decision_type: AgentDecisionType
    reasoning_summary: str
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    final_response: str | None = None
    escalation_reason: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_decision_shape(self) -> "AgentDecision":
        if self.decision_type == AgentDecisionType.TOOL_CALL:
            if not self.tool_name:
                raise ValueError("tool_call decisions require tool_name")
            if self.tool_arguments is None or not isinstance(self.tool_arguments, dict):
                raise ValueError("tool_call decisions require object tool_arguments")
        if self.decision_type in {AgentDecisionType.FINAL_RESPONSE, AgentDecisionType.FAIL}:
            if not self.final_response:
                raise ValueError(f"{self.decision_type.value} decisions require final_response")
        if self.decision_type == AgentDecisionType.ESCALATE and not self.escalation_reason:
            raise ValueError("escalate decisions require escalation_reason")
        return self


class AgentDecisionTrace(BaseModel):
    step: int
    decision_type: AgentDecisionType
    reasoning_summary: str
    tool_name: str | None = None
    tool_success: bool | None = None
    observation: str | None = None
