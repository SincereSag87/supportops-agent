from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuditEventType(StrEnum):
    REQUEST_RECEIVED = "request_received"
    MODEL_CALLED = "model_called"
    TOOL_SELECTED = "tool_selected"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    POLICY_CHECKED = "policy_checked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    ACTION_EXECUTED = "action_executed"
    ACTION_BLOCKED = "action_blocked"
    APPROVAL_CONSUMED = "approval_consumed"
    ACTION_REVERSED = "action_reversed"
    ESCALATED = "escalated"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_FAILED = "request_failed"


class AuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str
    tool_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    success: bool | None = None
