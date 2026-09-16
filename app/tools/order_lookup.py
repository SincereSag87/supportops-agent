from uuid import uuid4

from pydantic import BaseModel

from app.domain.orders import Order
from app.repositories.base import SupportDomainError
from app.support.service import SupportService
from app.tools.base import Tool
from app.tools.models import ToolResult, ToolRiskLevel


class OrderLookupInput(BaseModel):
    order_id: str


class CustomerOrdersInput(BaseModel):
    customer_id: str


class OrderLookupOutput(BaseModel):
    order: Order
    remaining_refundable_amount: str


class CustomerOrdersOutput(BaseModel):
    orders: list[Order]


class OrderLookupTool(Tool):
    name = "order_lookup"
    description = "Fetch synthetic order details by order id."
    input_model = OrderLookupInput
    output_model = OrderLookupOutput
    risk_level = ToolRiskLevel.READ_ONLY

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            order = self.service.get_order(data.order_id)
            output = self.output_model(
                order=order,
                remaining_refundable_amount=str(order.remaining_refundable_amount),
            )
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))


class ListCustomerOrdersTool(Tool):
    name = "list_customer_orders"
    description = "List synthetic orders for a customer."
    input_model = CustomerOrdersInput
    output_model = CustomerOrdersOutput
    risk_level = ToolRiskLevel.READ_ONLY

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            output = self.output_model(orders=self.service.get_customer_orders(data.customer_id))
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))
