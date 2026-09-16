from decimal import Decimal

from app.domain.orders import OrderStatus
from app.support.dataset import seed_customers, seed_orders, seed_refund_policy, seed_tickets


def test_synthetic_dataset_customer_ids_are_deterministic() -> None:
    customers = seed_customers()

    assert [customer.customer_id for customer in customers] == [
        "CUS-1001",
        "CUS-1002",
        "CUS-1003",
        "CUS-1004",
        "CUS-1005",
    ]
    assert all(customer.email.endswith("@example.test") for customer in customers)


def test_expected_orders_and_future_scenario_cases_exist() -> None:
    orders = {order.order_id: order for order in seed_orders()}

    assert orders["ORD-1001"].items[0].product_name == "Wireless Headphones"
    assert orders["ORD-1001"].total == Decimal("79.99")
    assert orders["ORD-1002"].total == Decimal("299.99")
    assert orders["ORD-1003"].total == Decimal("749.99")
    assert orders["ORD-1004"].delivered_at is not None
    assert orders["ORD-1005"].status == OrderStatus.SHIPPED
    assert len(orders["ORD-1006"].items) == 2
    assert len(orders) == 9


def test_policy_and_tickets_exist() -> None:
    policy = seed_refund_policy()
    tickets = seed_tickets()

    assert policy.policy_version == "northstar-refund-v1"
    assert policy.auto_refund_limit == Decimal("100.00")
    assert policy.approval_refund_limit == Decimal("500.00")
    assert len(tickets) == 5
    assert tickets[0].customer_id == "CUS-1001"
