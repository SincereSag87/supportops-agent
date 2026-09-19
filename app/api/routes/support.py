from fastapi import APIRouter, Depends

from app.api.dependencies import ServiceContainer, get_container

router = APIRouter(tags=["support"])
ContainerDep = Depends(get_container)


@router.get("/customers")
def list_customers(container: ServiceContainer = ContainerDep) -> list[dict[str, str]]:
    return [
        {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
            "status": customer.status.value,
        }
        for customer in container.support_service.customers.list()
    ]


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: str,
    container: ServiceContainer = ContainerDep,
) -> dict[str, object]:
    customer = container.support_service.get_customer(customer_id)
    orders = container.support_service.get_customer_orders(customer_id)
    open_tickets = [
        ticket
        for ticket in container.support_service.get_customer_tickets(customer_id)
        if ticket.status.value not in {"closed", "resolved"}
    ]
    return {
        **customer.model_dump(mode="json"),
        "order_ids": [order.order_id for order in orders],
        "open_ticket_ids": [ticket.ticket_id for ticket in open_tickets],
    }


@router.get("/customers/{customer_id}/orders")
def customer_orders(
    customer_id: str,
    container: ServiceContainer = ContainerDep,
) -> list[dict[str, object]]:
    return [
        _serialize_order(order)
        for order in container.support_service.get_customer_orders(customer_id)
    ]


@router.get("/orders/{order_id}")
def get_order(
    order_id: str,
    container: ServiceContainer = ContainerDep,
) -> dict[str, object]:
    return _serialize_order(container.support_service.get_order(order_id))


@router.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: str,
    container: ServiceContainer = ContainerDep,
) -> dict[str, object]:
    return container.support_service.get_ticket(ticket_id).model_dump(mode="json")


@router.get("/customers/{customer_id}/tickets")
def customer_tickets(
    customer_id: str,
    container: ServiceContainer = ContainerDep,
) -> list[dict[str, object]]:
    return [
        ticket.model_dump(mode="json")
        for ticket in container.support_service.get_customer_tickets(customer_id)
    ]


@router.get("/policies/refund")
def refund_policy(container: ServiceContainer = ContainerDep) -> dict[str, object]:
    return container.support_service.get_refund_policy().model_dump(mode="json")


def _serialize_order(order) -> dict[str, object]:
    data = order.model_dump(mode="json")
    data["remaining_refundable_amount"] = str(order.remaining_refundable_amount)
    return data
