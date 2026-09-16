from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class OrderItem(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("quantity must be greater than 0")
        return value

    @field_validator("unit_price")
    @classmethod
    def unit_price_must_be_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError("unit_price must be greater than or equal to 0")
        return value

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class Order(BaseModel):
    order_id: str
    customer_id: str
    items: list[OrderItem]
    subtotal: Decimal
    tax: Decimal = Decimal("0.00")
    total: Decimal
    currency: str = "USD"
    status: OrderStatus
    ordered_at: datetime
    delivered_at: datetime | None = None
    refund_total: Decimal = Decimal("0.00")
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    @field_validator("subtotal", "tax", "total", "refund_total")
    @classmethod
    def money_must_be_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError("money values must be greater than or equal to 0")
        return value

    @model_validator(mode="after")
    def validate_totals(self) -> "Order":
        item_total = sum((item.line_total for item in self.items), Decimal("0.00"))
        if self.subtotal != item_total:
            raise ValueError("subtotal must equal the sum of order item totals")
        if self.subtotal + self.tax != self.total:
            raise ValueError("total must equal subtotal plus tax")
        if self.refund_total > self.total:
            raise ValueError("refund_total cannot exceed total")
        return self

    @property
    def remaining_refundable_amount(self) -> Decimal:
        return self.total - self.refund_total
