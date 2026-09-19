from typing import Any
from uuid import UUID

from app.audit.models import AuditEvent, AuditEventType
from app.audit.repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    def record(
        self,
        request_id: UUID,
        event_type: AuditEventType,
        actor: str,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            request_id=request_id,
            event_type=event_type,
            actor=actor,
            tool_name=tool_name,
            details=details or {},
            success=success,
        )
        return self.repository.append(event)

    def list_for_request(self, request_id: UUID) -> list[AuditEvent]:
        return self.repository.list_for_request(request_id)

    def list_all(self) -> list[AuditEvent]:
        return self.repository.list_all()
