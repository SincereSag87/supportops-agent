from abc import ABC, abstractmethod

from app.domain.customers import Customer
from app.domain.orders import Order
from app.domain.policies import RefundPolicy
from app.domain.refunds import RefundRecord
from app.domain.tickets import SupportTicket


class SupportDomainError(RuntimeError):
    """Base support domain error."""


class CustomerNotFoundError(SupportDomainError):
    """Raised when a customer cannot be found."""


class OrderNotFoundError(SupportDomainError):
    """Raised when an order cannot be found."""


class TicketNotFoundError(SupportDomainError):
    """Raised when a ticket cannot be found."""


class RefundNotFoundError(SupportDomainError):
    """Raised when a refund cannot be found."""


class InvalidRefundAmountError(SupportDomainError):
    """Raised when a refund amount is invalid."""


class RefundExceedsRemainingAmountError(SupportDomainError):
    """Raised when a refund exceeds the remaining refundable order amount."""


class DuplicateRecordError(SupportDomainError):
    """Raised when a duplicate record would be created."""


class InvalidOrderStateError(SupportDomainError):
    """Raised when an order is not in a valid state for the requested operation."""


class IdempotencyConflictError(SupportDomainError):
    """Raised when an idempotency key is reused for conflicting input."""


class CustomerRepository(ABC):
    @abstractmethod
    def get(self, customer_id: str) -> Customer:
        """Return a customer by id."""

    @abstractmethod
    def find_by_email(self, email: str) -> Customer:
        """Return a customer by email."""

    @abstractmethod
    def list(self) -> list[Customer]:
        """Return all customers."""


class OrderRepository(ABC):
    @abstractmethod
    def get(self, order_id: str) -> Order:
        """Return an order by id."""

    @abstractmethod
    def list_for_customer(self, customer_id: str) -> list[Order]:
        """Return orders for a customer."""

    @abstractmethod
    def save(self, order: Order) -> Order:
        """Save an order."""


class TicketRepository(ABC):
    @abstractmethod
    def get(self, ticket_id: str) -> SupportTicket:
        """Return a ticket by id."""

    @abstractmethod
    def list_for_customer(self, customer_id: str) -> list[SupportTicket]:
        """Return tickets for a customer."""

    @abstractmethod
    def save(self, ticket: SupportTicket) -> SupportTicket:
        """Save a ticket."""


class RefundRepository(ABC):
    @abstractmethod
    def get(self, refund_id: str) -> RefundRecord:
        """Return a refund by id."""

    @abstractmethod
    def find_by_idempotency_key(self, key: str) -> RefundRecord | None:
        """Return a refund by idempotency key, if present."""

    @abstractmethod
    def list_for_order(self, order_id: str) -> list[RefundRecord]:
        """Return refunds for an order."""

    @abstractmethod
    def save(self, refund: RefundRecord) -> RefundRecord:
        """Save a refund."""


class PolicyRepository(ABC):
    @abstractmethod
    def get_refund_policy(self) -> RefundPolicy:
        """Return the current refund policy."""
