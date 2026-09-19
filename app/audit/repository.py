from abc import ABC, abstractmethod
from uuid import UUID

from app.audit.models import AuditEvent


class AuditRepository(ABC):
    @abstractmethod
    def append(self, event: AuditEvent) -> AuditEvent:
        """Append one audit event."""

    @abstractmethod
    def list_for_request(self, request_id: UUID) -> list[AuditEvent]:
        """Return events for a request."""

    @abstractmethod
    def list_all(self) -> list[AuditEvent]:
        """Return all audit events."""


class InMemoryAuditRepository(AuditRepository):
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self._events.append(event.model_copy(deep=True))
        return event.model_copy(deep=True)

    def list_for_request(self, request_id: UUID) -> list[AuditEvent]:
        return [
            event.model_copy(deep=True)
            for event in self._events
            if event.request_id == request_id
        ]

    def list_all(self) -> list[AuditEvent]:
        return [event.model_copy(deep=True) for event in self._events]
