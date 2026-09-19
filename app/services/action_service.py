from uuid import UUID, uuid4

from pydantic import ValidationError

from app.approvals.service import ApprovalService
from app.audit.models import AuditEventType
from app.audit.service import AuditService
from app.policies.models import PolicyDecision, PolicyDecisionResult, ProposedAction
from app.tools.models import ToolResult, ToolRiskLevel
from app.tools.registry import ToolRegistry


class ActionNotAllowedError(RuntimeError):
    """Raised when policy or safety does not allow action execution."""


class ActionExecutionError(RuntimeError):
    """Raised when an action cannot be executed safely."""


AUTO_EXECUTABLE_HIGH_RISK_TOOLS = {"issue_refund"}


class ActionService:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        approval_service: ApprovalService,
        audit_service: AuditService,
    ) -> None:
        self.tool_registry = tool_registry
        self.approval_service = approval_service
        self.audit_service = audit_service

    def execute(
        self,
        request_id: UUID,
        action: ProposedAction,
        policy_decision: PolicyDecisionResult,
        approval_id: UUID | None = None,
    ) -> ToolResult:
        if not self._is_execution_allowed(action, policy_decision, approval_id):
            raise ActionNotAllowedError("Policy decision does not allow execution")

        approval = None
        if policy_decision.decision == PolicyDecision.REQUIRE_APPROVAL:
            approval = self.approval_service.verify_for_action(approval_id, action)

        tool = self.tool_registry.get(action.tool_name)
        try:
            validated = tool.input_model.model_validate(action.arguments)
        except ValidationError as exc:
            raise ActionExecutionError(f"Approved action arguments are invalid: {exc}") from exc

        try:
            self.audit_service.record(
                request_id=request_id,
                event_type=AuditEventType.TOOL_STARTED,
                actor="action_service",
                tool_name=action.tool_name,
                details={"policy_decision": policy_decision.decision.value},
                success=None,
            )
        except Exception as exc:
            raise ActionExecutionError(
                "Critical pre-execution audit logging failed; action was not executed"
            ) from exc
        result = tool.execute(validated)
        try:
            self.audit_service.record(
                request_id=request_id,
                event_type=(
                    AuditEventType.TOOL_COMPLETED if result.success else AuditEventType.TOOL_FAILED
                ),
                actor="action_service",
                tool_name=action.tool_name,
                details={
                    "success": result.success,
                    "error": result.error,
                },
                success=result.success,
            )
        except Exception as exc:
            raise ActionExecutionError(
                "Post-execution audit logging failed after tool execution"
            ) from exc
        if not result.success:
            raise ActionExecutionError(result.error or "Tool execution failed")

        action_id = uuid4()
        try:
            self.audit_service.record(
                request_id=request_id,
                event_type=AuditEventType.ACTION_EXECUTED,
                actor="action_service",
                tool_name=action.tool_name,
                details={
                    "action_id": str(action_id),
                    "policy_decision": policy_decision.decision.value,
                },
                success=True,
            )
        except Exception as exc:
            raise ActionExecutionError(
                "Post-execution action audit logging failed after tool execution"
            ) from exc
        if approval is not None:
            self.approval_service.consume(approval.approval_id, action_id)
            self.audit_service.record(
                request_id=request_id,
                event_type=AuditEventType.APPROVAL_CONSUMED,
                actor="approval_service",
                tool_name=action.tool_name,
                details={"approval_id": str(approval.approval_id), "action_id": str(action_id)},
                success=True,
            )
        return result

    def _is_execution_allowed(
        self,
        action: ProposedAction,
        policy_decision: PolicyDecisionResult,
        approval_id: UUID | None,
    ) -> bool:
        if policy_decision.decision == PolicyDecision.ALLOW:
            if action.risk_level != ToolRiskLevel.HIGH_RISK_WRITE:
                return True
            return action.tool_name in AUTO_EXECUTABLE_HIGH_RISK_TOOLS and approval_id is None
        if policy_decision.decision == PolicyDecision.REQUIRE_APPROVAL:
            return approval_id is not None
        return False
