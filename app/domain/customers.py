from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class Customer(BaseModel):
    customer_id: str
    name: str
    email: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: CustomerStatus = CustomerStatus.ACTIVE
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def require_synthetic_email(cls, value: str) -> str:
        if not value.endswith("@example.test"):
            raise ValueError("synthetic customers must use example.test email addresses")
        return value
