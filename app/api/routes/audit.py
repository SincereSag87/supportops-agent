from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import ServiceContainer, get_container
from app.api.models import serialize_audit_event

router = APIRouter(prefix="/audit", tags=["audit"])
ContainerDep = Depends(get_container)


@router.get("/requests/{request_id}")
def request_audit(
    request_id: UUID,
    container: ServiceContainer = ContainerDep,
) -> list[dict]:
    events = container.audit_service.list_for_request(request_id)
    return [serialize_audit_event(event) for event in events]


@router.get("/recent")
def recent_audit(
    limit: int = Query(default=50, ge=1, le=100),
    container: ServiceContainer = ContainerDep,
) -> list[dict]:
    events = container.audit_service.list_all()
    return [serialize_audit_event(event) for event in events[-limit:]]
