from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import ServiceContainer, get_container
from app.api.models import ApprovalDecisionAPI, serialize_agent_result, serialize_approval
from app.api.routes.agent import record_agent_metrics
from app.observability.tracing import timer

router = APIRouter(prefix="/approvals", tags=["approvals"])
ContainerDep = Depends(get_container)


@router.get("/pending")
def pending_approvals(container: ServiceContainer = ContainerDep) -> list[dict]:
    return [serialize_approval(approval) for approval in container.approval_service.list_pending()]


@router.get("/{approval_id}")
def get_approval(
    approval_id: UUID,
    container: ServiceContainer = ContainerDep,
) -> dict:
    return serialize_approval(container.approval_service.get(approval_id))


@router.post("/{approval_id}/approve")
def approve(
    approval_id: UUID,
    decision: ApprovalDecisionAPI,
    container: ServiceContainer = ContainerDep,
):
    with timer() as elapsed_ms:
        result = container.agent_service.resolve_approval(
            approval_id,
            approved=True,
            decided_by=decision.actor,
            comment=decision.comment,
        )
    container.metrics_store.increment("approvals.granted")
    record_agent_metrics(container, result, None, elapsed_ms())
    return serialize_agent_result(result)


@router.post("/{approval_id}/deny")
def deny(
    approval_id: UUID,
    decision: ApprovalDecisionAPI,
    container: ServiceContainer = ContainerDep,
):
    with timer() as elapsed_ms:
        result = container.agent_service.resolve_approval(
            approval_id,
            approved=False,
            decided_by=decision.actor,
            comment=decision.comment,
        )
    container.metrics_store.increment("approvals.denied")
    record_agent_metrics(container, result, None, elapsed_ms())
    return serialize_agent_result(result)
