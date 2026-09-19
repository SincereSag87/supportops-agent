from datetime import UTC, datetime
from uuid import UUID

from app.approvals.repository import ApprovalNotFoundError, ApprovalRepository
from app.policies.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    PolicyDecisionResult,
    ProposedAction,
)


class ApprovalDeniedError(RuntimeError):
    """Raised when an approval is denied."""


class ApprovalConsumedError(RuntimeError):
    """Raised when an approval was already consumed."""


class ApprovalActionMismatchError(RuntimeError):
    """Raised when an approval does not authorize the requested action."""


class ApprovalRequiredError(RuntimeError):
    """Raised when an action requires approval but none was supplied."""


class ApprovalService:
    def __init__(self, repository: ApprovalRepository) -> None:
        self.repository = repository

    def create_request(
        self,
        request_id: UUID,
        action: ProposedAction,
        reason: str,
        policy_decision: PolicyDecisionResult | None = None,
    ) -> ApprovalRequest:
        approval = ApprovalRequest(
            request_id=request_id,
            action=action,
            reason=reason,
            status=ApprovalStatus.PENDING,
            policy_decision=policy_decision,
        )
        return self.repository.save(approval)

    def get(self, approval_id: UUID) -> ApprovalRequest:
        return self.repository.get(approval_id)

    def list_pending(self) -> list[ApprovalRequest]:
        return self.repository.list_pending()

    def approve(
        self,
        approval_id: UUID,
        decided_by: str,
        comment: str | None = None,
    ) -> ApprovalDecision:
        approval = self.repository.get(approval_id)
        if approval.consumed_at is not None:
            raise ApprovalConsumedError("Approval has already been consumed")
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalRequiredError("Approval has already been decided")
        updated = approval.model_copy(update={"status": ApprovalStatus.APPROVED})
        self.repository.save(updated)
        return ApprovalDecision(
            approval_id=approval_id,
            status=ApprovalStatus.APPROVED,
            decided_by=decided_by,
            comment=comment,
        )

    def deny(
        self,
        approval_id: UUID,
        decided_by: str,
        comment: str | None = None,
    ) -> ApprovalDecision:
        approval = self.repository.get(approval_id)
        if approval.consumed_at is not None:
            raise ApprovalConsumedError("Approval has already been consumed")
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalRequiredError("Approval has already been decided")
        updated = approval.model_copy(update={"status": ApprovalStatus.DENIED})
        self.repository.save(updated)
        return ApprovalDecision(
            approval_id=approval_id,
            status=ApprovalStatus.DENIED,
            decided_by=decided_by,
            comment=comment,
        )

    def expire(self, approval_id: UUID) -> ApprovalRequest:
        approval = self.repository.get(approval_id)
        expired = approval.model_copy(update={"status": ApprovalStatus.EXPIRED})
        return self.repository.save(expired)

    def verify_for_action(
        self,
        approval_id: UUID | None,
        action: ProposedAction,
    ) -> ApprovalRequest:
        if approval_id is None:
            raise ApprovalRequiredError("Approval is required for this action")
        approval = self.repository.get(approval_id)
        if approval.status == ApprovalStatus.DENIED:
            raise ApprovalDeniedError("Approval was denied")
        if approval.status != ApprovalStatus.APPROVED:
            raise ApprovalRequiredError("Approval has not been granted")
        if approval.consumed_at is not None:
            raise ApprovalConsumedError("Approval has already been consumed")
        if approval.action.model_dump(mode="json") != action.model_dump(mode="json"):
            raise ApprovalActionMismatchError("Approval does not match the requested action")
        return approval

    def consume(self, approval_id: UUID, executed_action_id: UUID) -> ApprovalRequest:
        approval = self.repository.get(approval_id)
        if approval.consumed_at is not None:
            raise ApprovalConsumedError("Approval has already been consumed")
        consumed = approval.model_copy(
            update={
                "consumed_at": datetime.now(UTC),
                "executed_action_id": executed_action_id,
            }
        )
        return self.repository.save(consumed)


__all__ = [
    "ApprovalActionMismatchError",
    "ApprovalConsumedError",
    "ApprovalDeniedError",
    "ApprovalNotFoundError",
    "ApprovalRequiredError",
    "ApprovalService",
]
