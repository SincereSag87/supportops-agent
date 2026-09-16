from app.domain.customers import Customer
from app.domain.orders import Order
from app.domain.policies import RefundPolicy
from app.domain.refunds import RefundRecord
from app.domain.tickets import SupportTicket
from app.repositories.base import (
    CustomerNotFoundError,
    CustomerRepository,
    DuplicateRecordError,
    OrderNotFoundError,
    OrderRepository,
    PolicyRepository,
    RefundNotFoundError,
    RefundRepository,
    TicketNotFoundError,
    TicketRepository,
)


class InMemoryCustomerRepository(CustomerRepository):
    def __init__(self, customers: list[Customer]) -> None:
        self._customers = {
            customer.customer_id: customer.model_copy(deep=True) for customer in customers
        }

    def get(self, customer_id: str) -> Customer:
        try:
            return self._customers[customer_id].model_copy(deep=True)
        except KeyError as exc:
            raise CustomerNotFoundError(f"Customer not found: {customer_id}") from exc

    def find_by_email(self, email: str) -> Customer:
        for customer in self._customers.values():
            if customer.email == email:
                return customer.model_copy(deep=True)
        raise CustomerNotFoundError(f"Customer not found for email: {email}")

    def list(self) -> list[Customer]:
        return [customer.model_copy(deep=True) for customer in self._customers.values()]


class InMemoryOrderRepository(OrderRepository):
    def __init__(self, orders: list[Order]) -> None:
        self._orders = {order.order_id: order.model_copy(deep=True) for order in orders}

    def get(self, order_id: str) -> Order:
        try:
            return self._orders[order_id].model_copy(deep=True)
        except KeyError as exc:
            raise OrderNotFoundError(f"Order not found: {order_id}") from exc

    def list_for_customer(self, customer_id: str) -> list[Order]:
        return [
            order.model_copy(deep=True)
            for order in self._orders.values()
            if order.customer_id == customer_id
        ]

    def save(self, order: Order) -> Order:
        self._orders[order.order_id] = order.model_copy(deep=True)
        return order.model_copy(deep=True)


class InMemoryTicketRepository(TicketRepository):
    def __init__(self, tickets: list[SupportTicket]) -> None:
        self._tickets = {ticket.ticket_id: ticket.model_copy(deep=True) for ticket in tickets}

    def get(self, ticket_id: str) -> SupportTicket:
        try:
            return self._tickets[ticket_id].model_copy(deep=True)
        except KeyError as exc:
            raise TicketNotFoundError(f"Ticket not found: {ticket_id}") from exc

    def list_for_customer(self, customer_id: str) -> list[SupportTicket]:
        return [
            ticket.model_copy(deep=True)
            for ticket in self._tickets.values()
            if ticket.customer_id == customer_id
        ]

    def save(self, ticket: SupportTicket) -> SupportTicket:
        self._tickets[ticket.ticket_id] = ticket.model_copy(deep=True)
        return ticket.model_copy(deep=True)


class InMemoryRefundRepository(RefundRepository):
    def __init__(self, refunds: list[RefundRecord]) -> None:
        self._refunds = {refund.refund_id: refund.model_copy(deep=True) for refund in refunds}

    def get(self, refund_id: str) -> RefundRecord:
        try:
            return self._refunds[refund_id].model_copy(deep=True)
        except KeyError as exc:
            raise RefundNotFoundError(f"Refund not found: {refund_id}") from exc

    def find_by_idempotency_key(self, key: str) -> RefundRecord | None:
        for refund in self._refunds.values():
            if refund.idempotency_key == key:
                return refund.model_copy(deep=True)
        return None

    def list_for_order(self, order_id: str) -> list[RefundRecord]:
        return [
            refund.model_copy(deep=True)
            for refund in self._refunds.values()
            if refund.order_id == order_id
        ]

    def save(self, refund: RefundRecord) -> RefundRecord:
        existing = self._refunds.get(refund.refund_id)
        if existing and existing.idempotency_key != refund.idempotency_key:
            raise DuplicateRecordError(f"Refund already exists: {refund.refund_id}")
        self._refunds[refund.refund_id] = refund.model_copy(deep=True)
        return refund.model_copy(deep=True)


class InMemoryPolicyRepository(PolicyRepository):
    def __init__(self, refund_policy: RefundPolicy) -> None:
        self._refund_policy = refund_policy.model_copy(deep=True)

    def get_refund_policy(self) -> RefundPolicy:
        return self._refund_policy.model_copy(deep=True)
