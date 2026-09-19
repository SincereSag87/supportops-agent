from fastapi import APIRouter, Depends

from app.api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/health", tags=["health"])
ContainerDep = Depends(get_container)


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "supportops-agent"}


@router.get("/ollama")
def ollama_health(container: ServiceContainer = ContainerDep) -> dict[str, object]:
    check = container.health_service.check()
    return {
        "reachable": check.ollama_reachable,
        "base_url": container.settings.ollama_base_url,
        "default_model": container.settings.default_model,
    }


@router.get("/state")
def state_health(container: ServiceContainer = ContainerDep) -> dict[str, int]:
    customers = container.support_service.customers.list()
    orders = [
        order
        for customer in customers
        for order in container.support_service.get_customer_orders(customer.customer_id)
    ]
    tickets = [
        ticket
        for customer in customers
        for ticket in container.support_service.get_customer_tickets(customer.customer_id)
    ]
    refunds = [
        refund
        for order in orders
        for refund in container.support_service.get_order_refunds(order.order_id)
    ]
    return {
        "customers": len(customers),
        "orders": len(orders),
        "tickets": len(tickets),
        "refunds": len(refunds),
        "pending_approvals": len(container.approval_service.list_pending()),
        "audit_events": len(container.audit_service.list_all()),
    }
