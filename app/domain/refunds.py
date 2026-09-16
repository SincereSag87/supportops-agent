from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class RefundStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class RefundRecord(BaseModel):
    refund_id: str
    order_id: str
    customer_id: str
    amount: Decimal
    currency: str = "USD"
    reason: str
    status: RefundStatus = RefundStatus.COMPLETED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    idempotency_key: str
    reversed_by_refund_id: str | None = None
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("refund amount must be greater than 0")
        return value
