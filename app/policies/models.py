from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.tools.models import ToolRiskLevel


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"
    ESCALATE = "escalate"


class ProposedAction(BaseModel):
    action_type: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: ToolRiskLevel
    reversible: bool = False
    rollback_tool: str | None = None
    rollback_arguments: dict[str, Any] | None = None
    estimated_value: Decimal | None = None


class PolicyDecisionResult(BaseModel):
    decision: PolicyDecision
    reason: str
    policy_name: str
    action: ProposedAction
    rule_results: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    action: ProposedAction
    reason: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ApprovalStatus = ApprovalStatus.PENDING
    policy_decision: PolicyDecisionResult | None = None
    consumed_at: datetime | None = None
    executed_action_id: UUID | None = None


class ApprovalDecision(BaseModel):
    approval_id: UUID
    status: ApprovalStatus
    decided_by: str
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    comment: str | None = None
