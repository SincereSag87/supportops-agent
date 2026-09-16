from decimal import Decimal

import pytest

from app.domain.orders import OrderStatus
from app.domain.tickets import TicketPriority, TicketStatus
from app.repositories.base import (
    CustomerNotFoundError,
    IdempotencyConflictError,
    InvalidOrderStateError,
    InvalidRefundAmountError,
    OrderNotFoundError,
    RefundExceedsRemainingAmountError,
)
from app.repositories.memory import (
    InMemoryCustomerRepository,
    InMemoryOrderRepository,
    InMemoryPolicyRepository,
    InMemoryRefundRepository,
    InMemoryTicketRepository,
)
from app.support.dataset import (
    seed_customers,
    seed_orders,
    seed_refund_policy,
    seed_refunds,
    seed_tickets,
)
from app.support.service import create_demo_support_service


def test_repositories_get_list_save_missing_and_isolation() -> None:
    customers = InMemoryCustomerRepository(seed_customers())
    orders = InMemoryOrderRepository(seed_orders())
    tickets = InMemoryTicketRepository(seed_tickets())
    refunds = InMemoryRefundRepository(seed_refunds())
    policies = InMemoryPolicyRepository(seed_refund_policy())

    assert customers.get("CUS-1001").name == "Jordan Lee"
    assert customers.find_by_email("jordan.lee@example.test").customer_id == "CUS-1001"
    assert len(customers.list()) == 5
    with pytest.raises(CustomerNotFoundError):
        customers.get("CUS-MISSING")

    order = orders.get("ORD-1001")
    order.refund_total = Decimal("10.00")
    assert orders.get("ORD-1001").refund_total == Decimal("0.00")
    saved = orders.save(order)
    assert saved.refund_total == Decimal("10.00")
    with pytest.raises(OrderNotFoundError):
        orders.get("ORD-MISSING")

    ticket = tickets.get("TIC-1001")
    tickets.save(ticket.model_copy(update={"status": TicketStatus.RESOLVED}))
    assert tickets.get("TIC-1001").status == TicketStatus.RESOLVED
    assert refunds.list_for_order("ORD-1001") == []
    assert policies.get_refund_policy().return_window_days == 30


def test_support_service_lookup_methods() -> None:
    service = create_demo_support_service()

    assert service.get_customer("CUS-1001").name == "Jordan Lee"
    assert service.get_customer_by_email("jordan.lee@example.test").customer_id == "CUS-1001"
    assert service.get_order("ORD-1001").items[0].product_name == "Wireless Headphones"
    assert len(service.get_customer_orders("CUS-1001")) == 2
    assert len(service.get_customer_tickets("CUS-1001")) == 2
    assert service.get_order_refunds("ORD-1001") == []
    assert service.get_refund_policy().policy_version == "northstar-refund-v1"


def test_create_and_update_ticket_service_behavior() -> None:
    service = create_demo_support_service()
    ticket = service.create_ticket(
        customer_id="CUS-1001",
        order_id="ORD-1001",
        subject="New synthetic ticket",
        description="Synthetic details",
        priority=TicketPriority.HIGH,
    )

    assert ticket.customer_id == "CUS-1001"
    assert ticket.priority == TicketPriority.HIGH

    updated = service.update_ticket_status(ticket.ticket_id, TicketStatus.RESOLVED, "Resolved")
    assert updated.status == TicketStatus.RESOLVED
    assert updated.resolution == "Resolved"

    with pytest.raises(CustomerNotFoundError):
        service.create_ticket("CUS-MISSING", "Subject", "Body")


def test_issue_refund_integrity_and_idempotency() -> None:
    service = create_demo_support_service()

    refund, created = service.issue_refund("ORD-1001", Decimal("10.00"), "damaged", "idem-1")
    replay, replay_created = service.issue_refund("ORD-1001", Decimal("10.00"), "damaged", "idem-1")
    order = service.get_order("ORD-1001")

    assert created is True
    assert replay_created is False
    assert replay.refund_id == refund.refund_id
    assert order.refund_total == Decimal("10.00")
    assert order.status == OrderStatus.PARTIALLY_REFUNDED

    with pytest.raises(IdempotencyConflictError):
        service.issue_refund("ORD-1001", Decimal("11.00"), "damaged", "idem-1")
    with pytest.raises(InvalidRefundAmountError):
        service.issue_refund("ORD-1001", Decimal("0.00"), "damaged", "idem-zero")
    with pytest.raises(InvalidRefundAmountError):
        service.issue_refund("ORD-1001", Decimal("-1.00"), "damaged", "idem-negative")
    with pytest.raises(RefundExceedsRemainingAmountError):
        service.issue_refund("ORD-1001", Decimal("1000.00"), "damaged", "idem-over")
    with pytest.raises(OrderNotFoundError):
        service.issue_refund("ORD-MISSING", Decimal("1.00"), "damaged", "idem-missing")
    with pytest.raises(InvalidOrderStateError):
        service.issue_refund("ORD-1007", Decimal("1.00"), "damaged", "idem-state")


def test_full_refund_and_reversal_behavior() -> None:
    service = create_demo_support_service()
    refund, _ = service.issue_refund("ORD-1001", Decimal("79.99"), "damaged", "idem-full")

    assert service.get_order("ORD-1001").status == OrderStatus.REFUNDED

    reversal, created = service.reverse_refund(refund.refund_id, "idem-reverse", "manual rollback")
    order = service.get_order("ORD-1001")
    original = service.refunds.get(refund.refund_id)

    assert created is True
    assert reversal.refund_id == f"REV-{refund.refund_id}"
    assert original.reversed_by_refund_id == reversal.refund_id
    assert order.refund_total == Decimal("0.00")
    assert order.status == OrderStatus.DELIVERED
    assert len(service.get_order_refunds("ORD-1001")) == 2

    replay, replay_created = service.reverse_refund(
        refund.refund_id,
        "idem-reverse",
        "manual rollback",
    )
    assert replay_created is False
    assert replay.refund_id == reversal.refund_id
    with pytest.raises(InvalidRefundAmountError):
        service.reverse_refund(refund.refund_id, "idem-reverse-2", "double reverse")


def test_fresh_services_reset_in_memory_state() -> None:
    first = create_demo_support_service()
    first.issue_refund("ORD-1001", Decimal("10.00"), "damaged", "idem-reset")

    second = create_demo_support_service()

    assert second.get_order("ORD-1001").refund_total == Decimal("0.00")
    assert second.get_order_refunds("ORD-1001") == []
