from decimal import Decimal

from pydantic import BaseModel, field_validator


class RefundPolicy(BaseModel):
    return_window_days: int
    auto_refund_limit: Decimal
    approval_refund_limit: Decimal
    requires_delivered_order: bool = True
    allowed_reasons: list[str]
    policy_version: str

    @field_validator("return_window_days")
    @classmethod
    def return_window_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("return_window_days must be greater than 0")
        return value

    @field_validator("auto_refund_limit", "approval_refund_limit")
    @classmethod
    def limits_must_be_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError("refund policy limits must be greater than or equal to 0")
        return value
