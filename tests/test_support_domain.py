from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.customers import Customer, CustomerStatus
from app.domain.orders import OrderItem, OrderStatus
from app.domain.policies import RefundPolicy
from app.domain.refunds import RefundRecord, RefundStatus
from app.domain.tickets import SupportTicket, TicketPriority, TicketStatus
from app.support.dataset import dt, seed_orders, seed_refund_policy


def test_customer_requires_synthetic_email() -> None:
    customer = Customer(
        customer_id="CUS-X",
        name="Synthetic Person",
        email="synthetic.person@example.test",
        status=CustomerStatus.ACTIVE,
    )

    assert customer.email.endswith("@example.test")
    with pytest.raises(ValidationError):
        Customer(customer_id="CUS-BAD", name="Bad Email", email="person@example.com")


def test_order_item_decimal_totals_and_order_status() -> None:
    item = OrderItem(sku="SKU-1", product_name="Widget", quantity=2, unit_price=Decimal("9.99"))

    assert item.line_total == Decimal("19.98")
    assert seed_orders()[0].remaining_refundable_amount == Decimal("79.99")
    assert OrderStatus.DELIVERED.value == "delivered"


def test_ticket_states() -> None:
    ticket = SupportTicket(
        ticket_id="TIC-X",
        customer_id="CUS-X",
        subject="Synthetic issue",
        description="Synthetic ticket description",
        status=TicketStatus.OPEN,
        priority=TicketPriority.NORMAL,
    )

    assert ticket.status == TicketStatus.OPEN
    assert TicketStatus.WAITING_APPROVAL.value == "waiting_approval"


def test_refund_states() -> None:
    refund = RefundRecord(
        refund_id="REF-X",
        order_id="ORD-X",
        customer_id="CUS-X",
        amount=Decimal("10.00"),
        reason="damaged",
        idempotency_key="refund-x",
    )

    assert refund.status == RefundStatus.COMPLETED
    assert refund.amount == Decimal("10.00")
    assert refund.completed_at is not None


def test_policy_serialization() -> None:
    policy = RefundPolicy(
        return_window_days=30,
        auto_refund_limit=Decimal("100.00"),
        approval_refund_limit=Decimal("500.00"),
        allowed_reasons=["damaged"],
        policy_version="test-v1",
    )

    assert policy.model_dump(mode="json")["auto_refund_limit"] == "100.00"
    assert seed_refund_policy().return_window_days == 30


def test_dataset_dates_are_deterministic() -> None:
    assert dt("2026-09-12T16:30:00").year == 2026
