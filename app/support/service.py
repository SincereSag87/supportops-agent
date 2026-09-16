from datetime import UTC, datetime
from decimal import Decimal

from app.domain.customers import Customer
from app.domain.orders import Order, OrderStatus
from app.domain.policies import RefundPolicy
from app.domain.refunds import RefundRecord, RefundStatus
from app.domain.tickets import SupportTicket, TicketPriority, TicketStatus
from app.repositories.base import (
    CustomerNotFoundError,
    CustomerRepository,
    IdempotencyConflictError,
    InvalidOrderStateError,
    InvalidRefundAmountError,
    OrderRepository,
    RefundExceedsRemainingAmountError,
    RefundRepository,
    TicketRepository,
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


class SupportService:
    def __init__(
        self,
        customers: CustomerRepository,
        orders: OrderRepository,
        tickets: TicketRepository,
        refunds: RefundRepository,
        policies: InMemoryPolicyRepository,
    ) -> None:
        self.customers = customers
        self.orders = orders
        self.tickets = tickets
        self.refunds = refunds
        self.policies = policies

    def get_customer(self, customer_id: str) -> Customer:
        return self.customers.get(customer_id)

    def get_customer_by_email(self, email: str) -> Customer:
        return self.customers.find_by_email(email)

    def get_order(self, order_id: str) -> Order:
        return self.orders.get(order_id)

    def get_customer_orders(self, customer_id: str) -> list[Order]:
        self.customers.get(customer_id)
        return self.orders.list_for_customer(customer_id)

    def get_ticket(self, ticket_id: str) -> SupportTicket:
        return self.tickets.get(ticket_id)

    def get_customer_tickets(self, customer_id: str) -> list[SupportTicket]:
        self.customers.get(customer_id)
        return self.tickets.list_for_customer(customer_id)

    def get_refund_policy(self) -> RefundPolicy:
        return self.policies.get_refund_policy()

    def get_order_refunds(self, order_id: str) -> list[RefundRecord]:
        self.orders.get(order_id)
        return self.refunds.list_for_order(order_id)

    def create_ticket(
        self,
        customer_id: str,
        subject: str,
        description: str,
        priority: TicketPriority = TicketPriority.NORMAL,
        order_id: str | None = None,
    ) -> SupportTicket:
        self.customers.get(customer_id)
        if order_id is not None:
            order = self.orders.get(order_id)
            if order.customer_id != customer_id:
                raise CustomerNotFoundError("Order does not belong to the requested customer")
        next_number = 1001 + len(self.tickets.list_for_customer(customer_id))
        ticket = SupportTicket(
            ticket_id=f"TIC-{customer_id.removeprefix('CUS-')}-{next_number}",
            customer_id=customer_id,
            order_id=order_id,
            subject=subject,
            description=description,
            priority=priority,
            status=TicketStatus.OPEN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return self.tickets.save(ticket)

    def update_ticket_status(
        self,
        ticket_id: str,
        status: TicketStatus,
        resolution: str | None = None,
    ) -> SupportTicket:
        ticket = self.tickets.get(ticket_id)
        updated = ticket.model_copy(
            update={"status": status, "resolution": resolution, "updated_at": datetime.now(UTC)}
        )
        return self.tickets.save(updated)

    def issue_refund(
        self,
        order_id: str,
        amount: Decimal,
        reason: str,
        idempotency_key: str,
    ) -> tuple[RefundRecord, bool]:
        order = self.orders.get(order_id)
        existing = self.refunds.find_by_idempotency_key(idempotency_key)
        if existing is not None:
            if (
                existing.order_id != order_id
                or existing.amount != amount
                or existing.reason != reason
                or existing.metadata.get("record_type") == "reversal"
            ):
                raise IdempotencyConflictError("Idempotency key was reused with conflicting input")
            return existing, False

        if amount <= Decimal("0"):
            raise InvalidRefundAmountError("Refund amount must be greater than 0")
        if order.status in {OrderStatus.CANCELLED, OrderStatus.PENDING, OrderStatus.PROCESSING}:
            raise InvalidOrderStateError(f"Order is not refundable in state: {order.status.value}")
        if amount > order.remaining_refundable_amount:
            raise RefundExceedsRemainingAmountError("Refund exceeds remaining refundable amount")

        refund = RefundRecord(
            refund_id=f"REF-{order_id}-{len(self.refunds.list_for_order(order_id)) + 1:03d}",
            order_id=order_id,
            customer_id=order.customer_id,
            amount=amount,
            currency=order.currency,
            reason=reason,
            status=RefundStatus.COMPLETED,
            idempotency_key=idempotency_key,
            metadata={"record_type": "refund"},
        )
        self.refunds.save(refund)
        new_total = order.refund_total + amount
        new_status = (
            OrderStatus.REFUNDED if new_total == order.total else OrderStatus.PARTIALLY_REFUNDED
        )
        self.orders.save(order.model_copy(update={"refund_total": new_total, "status": new_status}))
        return refund, True

    def reverse_refund(
        self,
        refund_id: str,
        idempotency_key: str,
        reason: str,
    ) -> tuple[RefundRecord, bool]:
        original = self.refunds.get(refund_id)
        existing = self.refunds.find_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.metadata.get("reverses_refund_id") != refund_id:
                raise IdempotencyConflictError("Idempotency key was reused with conflicting input")
            return existing, False
        if original.status != RefundStatus.COMPLETED:
            raise InvalidRefundAmountError("Only completed refunds can be reversed")
        if original.reversed_by_refund_id is not None:
            raise InvalidRefundAmountError("Refund has already been reversed")

        order = self.orders.get(original.order_id)
        reversal = RefundRecord(
            refund_id=f"REV-{refund_id}",
            order_id=original.order_id,
            customer_id=original.customer_id,
            amount=original.amount,
            currency=original.currency,
            reason=reason,
            status=RefundStatus.REVERSED,
            idempotency_key=idempotency_key,
            metadata={"record_type": "reversal", "reverses_refund_id": refund_id},
        )
        self.refunds.save(reversal)
        self.refunds.save(original.model_copy(update={"reversed_by_refund_id": reversal.refund_id}))
        restored_total = order.refund_total - original.amount
        restored_status = (
            OrderStatus.DELIVERED
            if restored_total == Decimal("0")
            else OrderStatus.PARTIALLY_REFUNDED
        )
        self.orders.save(
            order.model_copy(update={"refund_total": restored_total, "status": restored_status})
        )
        return reversal, True


def create_demo_support_service() -> SupportService:
    return SupportService(
        customers=InMemoryCustomerRepository(seed_customers()),
        orders=InMemoryOrderRepository(seed_orders()),
        tickets=InMemoryTicketRepository(seed_tickets()),
        refunds=InMemoryRefundRepository(seed_refunds()),
        policies=InMemoryPolicyRepository(seed_refund_policy()),
    )
