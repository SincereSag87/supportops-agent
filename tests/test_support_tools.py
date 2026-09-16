from decimal import Decimal

from app.domain.tickets import TicketPriority, TicketStatus
from app.support.service import create_demo_support_service
from app.tools.customer_lookup import CustomerEmailLookupInput, CustomerLookupInput
from app.tools.models import ToolRiskLevel
from app.tools.order_lookup import CustomerOrdersInput, OrderLookupInput
from app.tools.policy_lookup import RefundPolicyLookupInput
from app.tools.refund_tools import IssueRefundInput, ReverseRefundInput
from app.tools.support_registry import create_support_tool_registry
from app.tools.ticket_tools import CreateTicketInput, TicketLookupInput, UpdateTicketStatusInput


def test_read_tools_return_structured_outputs() -> None:
    service = create_demo_support_service()
    registry = create_support_tool_registry(service)

    customer_result = registry.get("customer_lookup").execute(
        CustomerLookupInput(customer_id="CUS-1001")
    )

    assert customer_result.success
    assert registry.get("customer_lookup_by_email").execute(
        CustomerEmailLookupInput(email="jordan.lee@example.test")
    ).success
    assert registry.get("order_lookup").execute(OrderLookupInput(order_id="ORD-1001")).success
    assert registry.get("list_customer_orders").execute(
        CustomerOrdersInput(customer_id="CUS-1001")
    ).success
    assert registry.get("refund_policy_lookup").execute(RefundPolicyLookupInput()).success
    assert registry.get("ticket_lookup").execute(TicketLookupInput(ticket_id="TIC-1001")).success


def test_create_ticket_tool_success_and_invalid_customer() -> None:
    tool = create_support_tool_registry(create_demo_support_service()).get("create_ticket")

    result = tool.execute(
        CreateTicketInput(
            customer_id="CUS-1001",
            order_id="ORD-1001",
            subject="Synthetic create",
            description="Create ticket from tool",
            priority=TicketPriority.NORMAL,
        )
    )
    missing = tool.execute(
        CreateTicketInput(
            customer_id="CUS-MISSING",
            subject="Bad create",
            description="Unknown customer",
        )
    )

    assert result.success is True
    assert result.output is not None
    assert result.output.ticket.customer_id == "CUS-1001"
    assert missing.success is False


def test_update_ticket_status_tool() -> None:
    tool = create_support_tool_registry(create_demo_support_service()).get("update_ticket_status")

    result = tool.execute(
        UpdateTicketStatusInput(
            ticket_id="TIC-1001",
            status=TicketStatus.RESOLVED,
            resolution="Synthetic resolution",
        )
    )
    missing = tool.execute(
        UpdateTicketStatusInput(ticket_id="TIC-MISSING", status=TicketStatus.CLOSED)
    )

    assert result.success is True
    assert result.output.ticket.status == TicketStatus.RESOLVED
    assert missing.success is False


def test_issue_refund_tool_success_partial_full_invalid_and_idempotent_replay() -> None:
    service = create_demo_support_service()
    tool = create_support_tool_registry(service).get("issue_refund")

    first = tool.execute(
        IssueRefundInput(
            order_id="ORD-1001",
            amount=Decimal("10.00"),
            reason="damaged",
            idempotency_key="tool-idem-1",
        )
    )
    replay = tool.execute(
        IssueRefundInput(
            order_id="ORD-1001",
            amount=Decimal("10.00"),
            reason="damaged",
            idempotency_key="tool-idem-1",
        )
    )
    zero = tool.execute(
        IssueRefundInput(
            order_id="ORD-1001",
            amount=Decimal("0.00"),
            reason="damaged",
            idempotency_key="tool-zero",
        )
    )
    over = tool.execute(
        IssueRefundInput(
            order_id="ORD-1001",
            amount=Decimal("1000.00"),
            reason="damaged",
            idempotency_key="tool-over",
        )
    )
    missing = tool.execute(
        IssueRefundInput(
            order_id="ORD-MISSING",
            amount=Decimal("1.00"),
            reason="damaged",
            idempotency_key="tool-missing",
        )
    )

    assert first.success is True
    assert first.output.order_refund_total == "10.00"
    assert first.output.order_status == "partially_refunded"
    assert replay.success is True
    assert replay.output.created is False
    assert service.get_order("ORD-1001").refund_total == Decimal("10.00")
    assert zero.success is False
    assert over.success is False
    assert missing.success is False

    full_service = create_demo_support_service()
    full = create_support_tool_registry(full_service).get("issue_refund").execute(
        IssueRefundInput(
            order_id="ORD-1001",
            amount=Decimal("79.99"),
            reason="damaged",
            idempotency_key="tool-full",
        )
    )
    assert full.success is True
    assert full.output.order_status == "refunded"


def test_reverse_refund_tool() -> None:
    service = create_demo_support_service()
    registry = create_support_tool_registry(service)
    issue = registry.get("issue_refund").execute(
        IssueRefundInput(
            order_id="ORD-1001",
            amount=Decimal("10.00"),
            reason="damaged",
            idempotency_key="reverse-source",
        )
    )

    reverse = registry.get("reverse_refund").execute(
        ReverseRefundInput(
            refund_id=issue.output.refund.refund_id,
            idempotency_key="reverse-idem",
            reason="controlled reversal",
        )
    )
    double_reverse = registry.get("reverse_refund").execute(
        ReverseRefundInput(
            refund_id=issue.output.refund.refund_id,
            idempotency_key="reverse-idem-2",
            reason="controlled reversal",
        )
    )

    assert reverse.success is True
    assert reverse.output.order_refund_total == "0.00"
    assert double_reverse.success is False


def test_support_tool_registry_expected_tools_risks_and_schema() -> None:
    registry = create_support_tool_registry(create_demo_support_service())
    risks = {tool.name: tool.risk_level for tool in registry.list_tools()}

    assert set(risks) == {
        "customer_lookup",
        "customer_lookup_by_email",
        "order_lookup",
        "list_customer_orders",
        "refund_policy_lookup",
        "ticket_lookup",
        "create_ticket",
        "update_ticket_status",
        "issue_refund",
        "reverse_refund",
    }
    assert risks["customer_lookup"] == ToolRiskLevel.READ_ONLY
    assert risks["create_ticket"] == ToolRiskLevel.LOW_RISK_WRITE
    assert risks["issue_refund"] == ToolRiskLevel.HIGH_RISK_WRITE
    schema = registry.get("issue_refund").schema()
    assert "amount" in schema.input_schema["properties"]
    assert schema.risk_level == ToolRiskLevel.HIGH_RISK_WRITE
