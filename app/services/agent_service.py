from uuid import UUID

from app.agent.models import AgentRequest, AgentStatus
from app.agent.results import AgentResult
from app.agent.runner import AgentRunner
from app.approvals.service import ApprovalService
from app.audit.models import AuditEventType
from app.audit.service import AuditService
from app.services.action_service import ActionExecutionError, ActionNotAllowedError, ActionService


class AgentService:
    def __init__(
        self,
        runner: AgentRunner,
        approval_service: ApprovalService | None = None,
        action_service: ActionService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.runner = runner
        self.approval_service = approval_service
        self.action_service = action_service
        self.audit_service = audit_service

    def handle_request(
        self,
        user_input: str,
        customer_id: str | None = None,
        model: str | None = None,
    ) -> AgentResult:
        request = AgentRequest(user_input=user_input, customer_id=customer_id)
        return self.runner.run(request, model=model)

    def resolve_approval(
        self,
        approval_id: UUID,
        approved: bool,
        decided_by: str,
        comment: str | None = None,
    ) -> AgentResult:
        if self.approval_service is None or self.action_service is None:
            raise RuntimeError("Approval workflow is not configured")

        approval = self.approval_service.get(approval_id)
        if approved:
            self.approval_service.approve(approval_id, decided_by=decided_by, comment=comment)
            if self.audit_service is not None:
                self.audit_service.record(
                    request_id=approval.request_id,
                    event_type=AuditEventType.APPROVAL_GRANTED,
                    actor=decided_by,
                    tool_name=approval.action.tool_name,
                    details={"approval_id": str(approval_id), "comment": comment or ""},
                    success=True,
                )
            policy_decision = approval.policy_decision
            if policy_decision is None:
                raise RuntimeError("Approval does not include a policy decision")
            try:
                result = self.action_service.execute(
                    request_id=approval.request_id,
                    action=approval.action,
                    policy_decision=policy_decision,
                    approval_id=approval_id,
                )
            except (ActionNotAllowedError, ActionExecutionError) as exc:
                return AgentResult(
                    request_id=approval.request_id,
                    status=AgentStatus.FAILED,
                    response=str(exc),
                    error=str(exc),
                )
            if self.audit_service is not None:
                self.audit_service.record(
                    request_id=approval.request_id,
                    event_type=AuditEventType.REQUEST_COMPLETED,
                    actor="agent_service",
                    tool_name=approval.action.tool_name,
                    details={"approval_id": str(approval_id)},
                    success=True,
                )
            return AgentResult(
                request_id=approval.request_id,
                status=AgentStatus.COMPLETED,
                response="Approved action executed successfully.",
                tool_results=[result],
            )

        self.approval_service.deny(approval_id, decided_by=decided_by, comment=comment)
        if self.audit_service is not None:
            self.audit_service.record(
                request_id=approval.request_id,
                event_type=AuditEventType.APPROVAL_DENIED,
                actor=decided_by,
                tool_name=approval.action.tool_name,
                details={"approval_id": str(approval_id), "comment": comment or ""},
                success=True,
            )
        return AgentResult(
            request_id=approval.request_id,
            status=AgentStatus.COMPLETED,
            response="Approval was denied. No action was executed.",
        )
