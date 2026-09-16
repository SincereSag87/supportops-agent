from app.support.service import SupportService, create_demo_support_service
from app.tools.customer_lookup import CustomerLookupByEmailTool, CustomerLookupTool
from app.tools.order_lookup import ListCustomerOrdersTool, OrderLookupTool
from app.tools.policy_lookup import RefundPolicyLookupTool
from app.tools.refund_tools import IssueRefundTool, ReverseRefundTool
from app.tools.registry import ToolRegistry
from app.tools.ticket_tools import CreateTicketTool, TicketLookupTool, UpdateTicketStatusTool


def create_support_tool_registry(service: SupportService | None = None) -> ToolRegistry:
    support_service = service or create_demo_support_service()
    registry = ToolRegistry()
    registry.register(CustomerLookupTool(support_service))
    registry.register(CustomerLookupByEmailTool(support_service))
    registry.register(OrderLookupTool(support_service))
    registry.register(ListCustomerOrdersTool(support_service))
    registry.register(RefundPolicyLookupTool(support_service))
    registry.register(TicketLookupTool(support_service))
    registry.register(CreateTicketTool(support_service))
    registry.register(UpdateTicketStatusTool(support_service))
    registry.register(IssueRefundTool(support_service))
    registry.register(ReverseRefundTool(support_service))
    return registry
