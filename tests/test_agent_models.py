from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.agent.models import AgentMessage, AgentMessageRole, AgentRequest, AgentStatus
from app.agent.results import AgentResult
from app.agent.state import AgentState
from app.audit.models import AuditEvent, AuditEventType
from app.policies.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    PolicyDecision,
    PolicyDecisionResult,
    ProposedAction,
)
from app.tools.models import ToolRiskLevel


def action() -> ProposedAction:
    return ProposedAction(
        action_type="demo",
        tool_name="echo",
        arguments={"message": "hello"},
        risk_level=ToolRiskLevel.READ_ONLY,
        reversible=True,
        rollback_tool="echo",
        rollback_arguments={"message": "rollback"},
        estimated_value=Decimal("79.99"),
    )


def test_agent_state_and_request_id_behavior() -> None:
    request = AgentRequest(user_input="Help me")
    state = AgentState(
        request=request,
        messages=[AgentMessage(role=AgentMessageRole.USER, content=request.user_input)],
    )

    assert isinstance(request.request_id, UUID)
    assert state.status == AgentStatus.RECEIVED
    assert state.step_count == 0
    assert state.messages[0].timestamp is not None


def test_agent_status_enum() -> None:
    assert AgentStatus.AWAITING_APPROVAL.value == "awaiting_approval"
    assert AgentStatus.COMPLETED.value == "completed"


def test_agent_result_serialization() -> None:
    request = AgentRequest(user_input="Done?")
    result = AgentResult(
        request_id=request.request_id,
        status=AgentStatus.COMPLETED,
        response="Done",
    )

    dumped = result.model_dump(mode="json")

    assert dumped["request_id"] == str(request.request_id)
    assert dumped["status"] == "completed"
    assert dumped["tool_calls"] == []


def test_policy_models_and_decimal_serialization() -> None:
    decision = PolicyDecisionResult(
        decision=PolicyDecision.ALLOW,
        reason="read-only demo action",
        policy_name="phase1-demo-policy",
        action=action(),
    )

    assert decision.decision == PolicyDecision.ALLOW
    assert PolicyDecision.REQUIRE_APPROVAL.value == "require_approval"
    assert PolicyDecision.DENY.value == "deny"
    assert PolicyDecision.ESCALATE.value == "escalate"
    assert decision.model_dump(mode="json")["action"]["estimated_value"] == "79.99"


def test_audit_models_timestamps_event_types_and_request_association() -> None:
    request = AgentRequest(user_input="Audit this")
    event = AuditEvent(
        request_id=request.request_id,
        event_type=AuditEventType.REQUEST_RECEIVED,
        actor="agent",
        success=True,
    )

    assert event.request_id == request.request_id
    assert event.timestamp is not None
    assert AuditEventType.TOOL_FAILED.value == "tool_failed"


def test_approval_models_pending_approve_deny_and_identity_immutability() -> None:
    request = AgentRequest(user_input="Approve this")
    approval = ApprovalRequest(
        request_id=request.request_id,
        action=action(),
        reason="High-risk action requires human review",
    )

    approved = ApprovalDecision(
        approval_id=approval.approval_id,
        status=ApprovalStatus.APPROVED,
        decided_by="ops-lead",
    )
    denied = ApprovalDecision(
        approval_id=approval.approval_id,
        status=ApprovalStatus.DENIED,
        decided_by="ops-lead",
    )

    assert approval.status == ApprovalStatus.PENDING
    assert approved.status == ApprovalStatus.APPROVED
    assert denied.status == ApprovalStatus.DENIED
    with pytest.raises(ValidationError):
        approval.approval_id = request.request_id
