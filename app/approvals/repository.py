from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID

from app.policies.models import ApprovalRequest, ApprovalStatus


class ApprovalNotFoundError(RuntimeError):
    """Raised when an approval request is not found."""


class ApprovalRepository(ABC):
    @abstractmethod
    def save(self, approval: ApprovalRequest) -> ApprovalRequest:
        """Save or replace an approval request."""

    @abstractmethod
    def get(self, approval_id: UUID) -> ApprovalRequest:
        """Return an approval request."""

    @abstractmethod
    def list_pending(self) -> list[ApprovalRequest]:
        """Return pending approval requests."""


class InMemoryApprovalRepository(ApprovalRepository):
    def __init__(self) -> None:
        self._approvals: dict[UUID, ApprovalRequest] = {}

    def save(self, approval: ApprovalRequest) -> ApprovalRequest:
        self._approvals[approval.approval_id] = approval.model_copy(deep=True)
        return approval.model_copy(deep=True)

    def get(self, approval_id: UUID) -> ApprovalRequest:
        try:
            return self._approvals[approval_id].model_copy(deep=True)
        except KeyError as exc:
            raise ApprovalNotFoundError(f"Approval not found: {approval_id}") from exc

    def list_pending(self) -> list[ApprovalRequest]:
        return [
            approval.model_copy(deep=True)
            for approval in self._approvals.values()
            if approval.status == ApprovalStatus.PENDING
        ]

    def consume(self, approval_id: UUID, executed_action_id: UUID) -> ApprovalRequest:
        approval = self.get(approval_id)
        consumed = approval.model_copy(
            update={
                "consumed_at": datetime.now(UTC),
                "executed_action_id": executed_action_id,
            }
        )
        return self.save(consumed)
