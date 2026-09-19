from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.results import AgentResult
from app.audit.models import AuditEvent
from app.policies.models import ApprovalRequest


class ErrorEnvelope(BaseModel):
    error: dict[str, str]


class AgentRequestAPI(BaseModel):
    user_input: str = Field(min_length=1)
    customer_id: str | None = None
    model: str | None = None


class ApprovalDecisionAPI(BaseModel):
    actor: str = Field(min_length=1)
    comment: str | None = Field(default=None, max_length=500)


class EvaluationRequestAPI(BaseModel):
    benchmark: str = "support-agent-demo"
    mode: str = "scripted"
    model: str | None = None
    case_id: str | None = None


class DemoResetRequest(BaseModel):
    confirm: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str


class AgentResponseAPI(BaseModel):
    request_id: UUID
    status: str
    response: str
    escalated: bool
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    approvals_required: list[dict[str, Any]]
    decision_trace: list[dict[str, Any]]
    error: str | None = None


def serialize_agent_result(result: AgentResult) -> AgentResponseAPI:
    return AgentResponseAPI(
        request_id=result.request_id,
        status=result.status.value,
        response=result.response,
        escalated=result.escalated,
        tool_calls=[call.model_dump(mode="json") for call in result.tool_calls],
        tool_results=[tool_result.model_dump(mode="json") for tool_result in result.tool_results],
        approvals_required=[
            serialize_approval(approval) for approval in result.approvals_required
        ],
        decision_trace=[
            {
                "decision_type": decision.decision_type.value,
                "reasoning_summary": decision.reasoning_summary,
                "tool_name": decision.tool_name,
                "confidence": decision.confidence,
            }
            for decision in result.decision_history
        ],
        error=result.error,
    )


def serialize_approval(approval: ApprovalRequest) -> dict[str, Any]:
    policy_decision = approval.policy_decision
    return {
        "approval_id": str(approval.approval_id),
        "request_id": str(approval.request_id),
        "tool_name": approval.action.tool_name,
        "action_type": approval.action.action_type,
        "amount": approval.action.arguments.get("amount"),
        "reason": approval.reason,
        "policy_decision": policy_decision.decision.value if policy_decision else None,
        "policy_reason": policy_decision.reason if policy_decision else None,
        "status": approval.status.value,
        "requested_at": approval.requested_at.isoformat(),
        "consumed_at": approval.consumed_at.isoformat() if approval.consumed_at else None,
    }


def serialize_audit_event(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": str(event.event_id),
        "request_id": str(event.request_id),
        "timestamp": event.timestamp.isoformat(),
        "event_type": event.event_type.value,
        "actor": event.actor,
        "tool_name": event.tool_name,
        "details": event.details,
        "success": event.success,
    }
