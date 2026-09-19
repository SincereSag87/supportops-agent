from decimal import Decimal
from uuid import uuid4

import pytest

from app.agent.models import AgentRequest, AgentStatus
from app.agent.runner import AgentRunner
from app.agent.safety import AgentSafetyController
from app.approvals.repository import ApprovalNotFoundError, InMemoryApprovalRepository
from app.approvals.service import (
    ApprovalActionMismatchError,
    ApprovalConsumedError,
    ApprovalDeniedError,
    ApprovalRequiredError,
    ApprovalService,
)
from app.audit.models import AuditEventType
from app.audit.repository import InMemoryAuditRepository
from app.audit.service import AuditService
from app.core.config import Settings
from app.llm.models import ChatMessage, ChatResponse
from app.policies.engine import PolicyEngine
from app.policies.models import ApprovalStatus, PolicyDecision, ProposedAction
from app.services.action_service import ActionNotAllowedError, ActionService
from app.support.service import create_demo_support_service
from app.tools.models import ToolRiskLevel
from app.tools.support_registry import create_support_tool_registry


class ScriptedProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses

    def generate(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse:
        return ChatResponse(content=self.responses.pop(0), model=model or "test", provider="test")


def decision_json(**kwargs) -> str:
    import json

    return json.dumps(kwargs)


def refund_action(order_id: str, amount: str, reason: str, key: str = "idem") -> ProposedAction:
    return ProposedAction(
        action_type="issue_refund",
        tool_name="issue_refund",
        arguments={
            "order_id": order_id,
            "amount": amount,
            "reason": reason,
            "idempotency_key": key,
        },
        risk_level=ToolRiskLevel.HIGH_RISK_WRITE,
        reversible=True,
        rollback_tool="reverse_refund",
        estimated_value=Decimal(amount),
    )


def reverse_action(refund_id: str = "REF-ORD-1001-001") -> ProposedAction:
    return ProposedAction(
        action_type="reverse_refund",
        tool_name="reverse_refund",
        arguments={
            "refund_id": refund_id,
            "idempotency_key": "reverse-idem",
            "reason": "manager reversal",
        },
        risk_level=ToolRiskLevel.HIGH_RISK_WRITE,
    )


def services():
    support = create_demo_support_service()
    registry = create_support_tool_registry(support)
    approvals = ApprovalService(InMemoryApprovalRepository())
    audit = AuditService(InMemoryAuditRepository())
    action_service = ActionService(registry, approvals, audit)
    policy = PolicyEngine(support)
    return support, registry, approvals, audit, action_service, policy


def test_policy_engine_refund_rules_and_trusted_context() -> None:
    support, _registry, _approvals, _audit, _action_service, policy = services()

    low = refund_action("ORD-1001", "79.99", "damaged")
    medium = refund_action("ORD-1002", "299.99", "defective")
    high = refund_action("ORD-1003", "749.99", "defective")
    old = refund_action("ORD-1004", "10.00", "damaged")
    undelivered = refund_action("ORD-1005", "1.00", "damaged")
    invalid_reason = refund_action("ORD-1001", "10.00", "changed_mind")
    wrong_customer = refund_action("ORD-1001", "10.00", "damaged")

    assert (
        policy.evaluate(low, policy.build_context(low, "CUS-1001")).decision
        == PolicyDecision.ALLOW
    )
    assert (
        policy.evaluate(medium, policy.build_context(medium, "CUS-1002")).decision
        == PolicyDecision.REQUIRE_APPROVAL
    )
    assert (
        policy.evaluate(high, policy.build_context(high, "CUS-1003")).decision
        == PolicyDecision.ESCALATE
    )
    assert (
        policy.evaluate(old, policy.build_context(old, "CUS-1004")).decision
        == PolicyDecision.DENY
    )
    assert (
        policy.evaluate(undelivered, policy.build_context(undelivered, "CUS-1001")).decision
        == PolicyDecision.DENY
    )
    assert (
        policy.evaluate(invalid_reason, policy.build_context(invalid_reason, "CUS-1001")).decision
        == PolicyDecision.ESCALATE
    )
    assert (
        policy.evaluate(wrong_customer, policy.build_context(wrong_customer, "CUS-1002")).decision
        == PolicyDecision.DENY
    )
    assert support.get_order("ORD-1001").total == Decimal("79.99")


def test_action_service_auto_refund_and_audit_sequence() -> None:
    support, _registry, _approvals, audit, action_service, policy = services()
    request_id = uuid4()
    action = refund_action("ORD-1001", "79.99", "damaged", "auto-low")
    decision = policy.evaluate(action, policy.build_context(action, "CUS-1001"))

    result = action_service.execute(request_id, action, decision)
    events = [event.event_type for event in audit.list_for_request(request_id)]

    assert result.success is True
    assert support.get_order("ORD-1001").refund_total == Decimal("79.99")
    assert events == [
        AuditEventType.TOOL_STARTED,
        AuditEventType.TOOL_COMPLETED,
        AuditEventType.ACTION_EXECUTED,
    ]


def test_approval_required_grants_once_denial_and_bypass_protection() -> None:
    support, _registry, approvals, audit, action_service, policy = services()
    request_id = uuid4()
    action = refund_action("ORD-1002", "299.99", "defective", "approval-medium")
    decision = policy.evaluate(action, policy.build_context(action, "CUS-1002"))
    approval = approvals.create_request(request_id, action, decision.reason, decision)

    with pytest.raises(ActionNotAllowedError):
        action_service.execute(request_id, action, decision)
    with pytest.raises(ApprovalNotFoundError):
        action_service.execute(request_id, action, decision, uuid4())

    denied = approvals.create_request(uuid4(), action, decision.reason, decision)
    approvals.deny(denied.approval_id, "manager")
    with pytest.raises(ApprovalDeniedError):
        action_service.execute(request_id, action, decision, denied.approval_id)

    other_action = refund_action("ORD-1002", "199.99", "defective", "other")
    mismatch = approvals.create_request(uuid4(), other_action, decision.reason, decision)
    approvals.approve(mismatch.approval_id, "manager")
    with pytest.raises(ApprovalActionMismatchError):
        action_service.execute(request_id, action, decision, mismatch.approval_id)

    approvals.approve(approval.approval_id, "manager", "Approved damaged item.")
    result = action_service.execute(request_id, action, decision, approval.approval_id)

    assert result.success is True
    assert support.get_order("ORD-1002").refund_total == Decimal("299.99")
    assert approvals.get(approval.approval_id).consumed_at is not None
    with pytest.raises(ApprovalConsumedError):
        action_service.execute(request_id, action, decision, approval.approval_id)
    assert AuditEventType.APPROVAL_CONSUMED in [
        event.event_type for event in audit.list_for_request(request_id)
    ]


def test_approval_repository_pending_and_duplicate_decisions() -> None:
    _support, _registry, approvals, _audit, _action_service, policy = services()
    action = refund_action("ORD-1002", "299.99", "defective")
    decision = policy.evaluate(action, policy.build_context(action, "CUS-1002"))
    approval = approvals.create_request(uuid4(), action, decision.reason, decision)

    assert approvals.list_pending()[0].approval_id == approval.approval_id
    first = approvals.approve(approval.approval_id, "manager")
    assert first.status == ApprovalStatus.APPROVED
    with pytest.raises(ApprovalRequiredError):
        approvals.deny(approval.approval_id, "manager")


def test_reversal_always_requires_approval() -> None:
    support, _registry, approvals, _audit, action_service, policy = services()
    original_action = refund_action("ORD-1001", "10.00", "damaged", "source-refund")
    original_decision = policy.evaluate(
        original_action,
        policy.build_context(original_action, "CUS-1001"),
    )
    action_service.execute(uuid4(), original_action, original_decision)
    reversal = reverse_action("REF-ORD-1001-001")
    decision = policy.evaluate(reversal, policy.build_context(reversal, "CUS-1001"))

    assert decision.decision == PolicyDecision.REQUIRE_APPROVAL
    approval = approvals.create_request(uuid4(), reversal, decision.reason, decision)
    approvals.approve(approval.approval_id, "manager")
    result = action_service.execute(approval.request_id, reversal, decision, approval.approval_id)

    assert result.success is True
    assert support.get_order("ORD-1001").refund_total == Decimal("0.00")


def test_agent_runner_policy_allow_approval_deny_and_escalate() -> None:
    support, registry, approvals, audit, action_service, policy = services()
    runner = AgentRunner(
        llm_provider=ScriptedProvider(
            [
                decision_json(
                    decision_type="tool_call",
                    reasoning_summary="Low-value refund can be proposed.",
                    tool_name="issue_refund",
                    tool_arguments={
                        "order_id": "ORD-1001",
                        "amount": "79.99",
                        "reason": "damaged",
                        "idempotency_key": "runner-low",
                    },
                ),
                decision_json(
                    decision_type="final_response",
                    reasoning_summary="Refund completed.",
                    final_response="Refund completed.",
                ),
            ]
        ),
        tool_registry=registry,
        safety_controller=AgentSafetyController(Settings(_env_file=None)),
        settings=Settings(_env_file=None),
        policy_engine=policy,
        action_service=action_service,
        audit_service=audit,
    )
    low_result = runner.run(AgentRequest(user_input="Refund damaged item.", customer_id="CUS-1001"))
    assert low_result.status == AgentStatus.COMPLETED
    assert support.get_order("ORD-1001").refund_total == Decimal("79.99")

    medium_runner = AgentRunner(
        llm_provider=ScriptedProvider(
            [
                decision_json(
                    decision_type="tool_call",
                    reasoning_summary="Medium refund requires approval.",
                    tool_name="issue_refund",
                    tool_arguments={
                        "order_id": "ORD-1002",
                        "amount": "299.99",
                        "reason": "defective",
                        "idempotency_key": "runner-medium",
                    },
                )
            ]
        ),
        tool_registry=registry,
        safety_controller=AgentSafetyController(Settings(_env_file=None)),
        settings=Settings(_env_file=None),
        policy_engine=policy,
        action_service=action_service,
        audit_service=audit,
    )
    medium_result = medium_runner.run(
        AgentRequest(user_input="Refund defective dock.", customer_id="CUS-1002")
    )
    assert medium_result.status == AgentStatus.AWAITING_APPROVAL
    assert medium_result.approvals_required
    assert approvals.get(medium_result.approvals_required[0].approval_id).status == (
        ApprovalStatus.PENDING
    )

    high_runner = AgentRunner(
        llm_provider=ScriptedProvider(
            [
                decision_json(
                    decision_type="tool_call",
                    reasoning_summary="High-value refund needs escalation.",
                    tool_name="issue_refund",
                    tool_arguments={
                        "order_id": "ORD-1003",
                        "amount": "749.99",
                        "reason": "defective",
                        "idempotency_key": "runner-high",
                    },
                )
            ]
        ),
        tool_registry=registry,
        safety_controller=AgentSafetyController(Settings(_env_file=None)),
        settings=Settings(_env_file=None),
        policy_engine=policy,
        action_service=action_service,
        audit_service=audit,
    )
    high_result = high_runner.run(AgentRequest(user_input="Refund bundle.", customer_id="CUS-1003"))
    assert high_result.status == AgentStatus.ESCALATED
