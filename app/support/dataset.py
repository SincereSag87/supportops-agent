from datetime import UTC, datetime
from decimal import Decimal

from app.domain.customers import Customer, CustomerStatus
from app.domain.orders import Order, OrderItem, OrderStatus
from app.domain.policies import RefundPolicy
from app.domain.refunds import RefundRecord
from app.domain.tickets import SupportTicket, TicketPriority, TicketStatus


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def seed_customers() -> list[Customer]:
    return [
        Customer(
            customer_id="CUS-1001",
            name="Jordan Lee",
            email="jordan.lee@example.test",
            created_at=dt("2026-01-10T09:00:00"),
            status=CustomerStatus.ACTIVE,
        ),
        Customer(
            customer_id="CUS-1002",
            name="Morgan Chen",
            email="morgan.chen@example.test",
            created_at=dt("2026-02-14T11:30:00"),
            status=CustomerStatus.ACTIVE,
        ),
        Customer(
            customer_id="CUS-1003",
            name="Avery Patel",
            email="avery.patel@example.test",
            created_at=dt("2026-03-05T15:45:00"),
            status=CustomerStatus.ACTIVE,
        ),
        Customer(
            customer_id="CUS-1004",
            name="Riley Gomez",
            email="riley.gomez@example.test",
            created_at=dt("2026-04-21T10:15:00"),
            status=CustomerStatus.ACTIVE,
        ),
        Customer(
            customer_id="CUS-1005",
            name="Taylor Brooks",
            email="taylor.brooks@example.test",
            created_at=dt("2026-05-19T13:20:00"),
            status=CustomerStatus.SUSPENDED,
        ),
    ]


def seed_orders() -> list[Order]:
    return [
        Order(
            order_id="ORD-1001",
            customer_id="CUS-1001",
            items=[
                OrderItem(
                    sku="NS-AUDIO-100",
                    product_name="Wireless Headphones",
                    quantity=1,
                    unit_price=Decimal("74.99"),
                )
            ],
            subtotal=Decimal("74.99"),
            tax=Decimal("5.00"),
            total=Decimal("79.99"),
            status=OrderStatus.DELIVERED,
            ordered_at=dt("2026-09-08T12:00:00"),
            delivered_at=dt("2026-09-12T16:30:00"),
        ),
        Order(
            order_id="ORD-1002",
            customer_id="CUS-1002",
            items=[
                OrderItem(
                    sku="NS-DOCK-200",
                    product_name="Laptop Docking Station",
                    quantity=1,
                    unit_price=Decimal("279.99"),
                )
            ],
            subtotal=Decimal("279.99"),
            tax=Decimal("20.00"),
            total=Decimal("299.99"),
            status=OrderStatus.DELIVERED,
            ordered_at=dt("2026-09-05T09:40:00"),
            delivered_at=dt("2026-09-10T14:10:00"),
        ),
        Order(
            order_id="ORD-1003",
            customer_id="CUS-1003",
            items=[
                OrderItem(
                    sku="NS-TAB-900",
                    product_name="Pro Tablet Bundle",
                    quantity=1,
                    unit_price=Decimal("699.99"),
                )
            ],
            subtotal=Decimal("699.99"),
            tax=Decimal("50.00"),
            total=Decimal("749.99"),
            status=OrderStatus.DELIVERED,
            ordered_at=dt("2026-09-01T08:00:00"),
            delivered_at=dt("2026-09-06T12:20:00"),
        ),
        Order(
            order_id="ORD-1004",
            customer_id="CUS-1004",
            items=[
                OrderItem(
                    sku="NS-KBD-110",
                    product_name="Mechanical Keyboard",
                    quantity=1,
                    unit_price=Decimal("119.99"),
                )
            ],
            subtotal=Decimal("119.99"),
            tax=Decimal("8.40"),
            total=Decimal("128.39"),
            status=OrderStatus.DELIVERED,
            ordered_at=dt("2026-07-20T17:15:00"),
            delivered_at=dt("2026-08-01T09:25:00"),
        ),
        Order(
            order_id="ORD-1005",
            customer_id="CUS-1001",
            items=[
                OrderItem(
                    sku="NS-CABLE-010",
                    product_name="USB-C Cable Pack",
                    quantity=1,
                    unit_price=Decimal("24.99"),
                )
            ],
            subtotal=Decimal("24.99"),
            tax=Decimal("1.75"),
            total=Decimal("26.74"),
            status=OrderStatus.SHIPPED,
            ordered_at=dt("2026-09-14T10:00:00"),
            delivered_at=None,
        ),
        Order(
            order_id="ORD-1006",
            customer_id="CUS-1002",
            items=[
                OrderItem(
                    sku="NS-MOUSE-050",
                    product_name="Ergonomic Mouse",
                    quantity=1,
                    unit_price=Decimal("39.99"),
                ),
                OrderItem(
                    sku="NS-PAD-020",
                    product_name="Desk Mat",
                    quantity=1,
                    unit_price=Decimal("19.99"),
                ),
            ],
            subtotal=Decimal("59.98"),
            tax=Decimal("4.20"),
            total=Decimal("64.18"),
            status=OrderStatus.DELIVERED,
            ordered_at=dt("2026-09-03T16:45:00"),
            delivered_at=dt("2026-09-09T11:10:00"),
        ),
        Order(
            order_id="ORD-1007",
            customer_id="CUS-1005",
            items=[
                OrderItem(
                    sku="NS-CAM-300",
                    product_name="Conference Webcam",
                    quantity=1,
                    unit_price=Decimal("89.99"),
                )
            ],
            subtotal=Decimal("89.99"),
            tax=Decimal("6.30"),
            total=Decimal("96.29"),
            status=OrderStatus.PROCESSING,
            ordered_at=dt("2026-09-15T09:30:00"),
            delivered_at=None,
        ),
        Order(
            order_id="ORD-1008",
            customer_id="CUS-1003",
            items=[
                OrderItem(
                    sku="NS-HUB-070",
                    product_name="Travel USB Hub",
                    quantity=2,
                    unit_price=Decimal("29.99"),
                )
            ],
            subtotal=Decimal("59.98"),
            tax=Decimal("4.20"),
            total=Decimal("64.18"),
            status=OrderStatus.DELIVERED,
            ordered_at=dt("2026-08-28T14:00:00"),
            delivered_at=dt("2026-09-02T13:00:00"),
        ),
        Order(
            order_id="ORD-1009",
            customer_id="CUS-1004",
            items=[
                OrderItem(
                    sku="NS-SPKR-400",
                    product_name="Portable Speaker",
                    quantity=1,
                    unit_price=Decimal("59.99"),
                )
            ],
            subtotal=Decimal("59.99"),
            tax=Decimal("4.20"),
            total=Decimal("64.19"),
            status=OrderStatus.CANCELLED,
            ordered_at=dt("2026-09-11T19:00:00"),
            delivered_at=None,
        ),
    ]


def seed_tickets() -> list[SupportTicket]:
    return [
        SupportTicket(
            ticket_id="TIC-1001",
            customer_id="CUS-1001",
            order_id="ORD-1001",
            subject="Damaged headphones",
            description="Wireless Headphones arrived damaged. Customer is asking about a refund.",
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
            created_at=dt("2026-09-13T10:00:00"),
            updated_at=dt("2026-09-13T10:00:00"),
        ),
        SupportTicket(
            ticket_id="TIC-1002",
            customer_id="CUS-1002",
            order_id="ORD-1002",
            subject="Docking station display issue",
            description="Laptop Docking Station does not detect an external display.",
            status=TicketStatus.IN_PROGRESS,
            priority=TicketPriority.HIGH,
            created_at=dt("2026-09-11T12:00:00"),
            updated_at=dt("2026-09-12T09:00:00"),
        ),
        SupportTicket(
            ticket_id="TIC-1003",
            customer_id="CUS-1003",
            order_id="ORD-1003",
            subject="High-value bundle refund request",
            description="Customer reports the Pro Tablet Bundle arrived defective.",
            status=TicketStatus.WAITING_APPROVAL,
            priority=TicketPriority.URGENT,
            created_at=dt("2026-09-07T15:00:00"),
            updated_at=dt("2026-09-08T08:30:00"),
        ),
        SupportTicket(
            ticket_id="TIC-1004",
            customer_id="CUS-1004",
            order_id="ORD-1004",
            subject="Keyboard return question",
            description="Customer asks whether an older delivered order can be returned.",
            status=TicketStatus.OPEN,
            priority=TicketPriority.LOW,
            created_at=dt("2026-09-14T13:45:00"),
            updated_at=dt("2026-09-14T13:45:00"),
        ),
        SupportTicket(
            ticket_id="TIC-1005",
            customer_id="CUS-1001",
            order_id="ORD-1005",
            subject="Cable pack delivery status",
            description="Customer asks when the shipped USB-C Cable Pack will arrive.",
            status=TicketStatus.WAITING_CUSTOMER,
            priority=TicketPriority.NORMAL,
            created_at=dt("2026-09-15T11:10:00"),
            updated_at=dt("2026-09-15T11:10:00"),
        ),
    ]


def seed_refunds() -> list[RefundRecord]:
    return []


def seed_refund_policy() -> RefundPolicy:
    return RefundPolicy(
        return_window_days=30,
        auto_refund_limit=Decimal("100.00"),
        approval_refund_limit=Decimal("500.00"),
        requires_delivered_order=True,
        allowed_reasons=["damaged", "defective", "missing_item", "wrong_item", "duplicate_charge"],
        policy_version="northstar-refund-v1",
    )
