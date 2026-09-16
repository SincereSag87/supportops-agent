from uuid import uuid4

from pydantic import BaseModel

from app.domain.customers import Customer
from app.repositories.base import SupportDomainError
from app.support.service import SupportService
from app.tools.base import Tool
from app.tools.models import ToolResult, ToolRiskLevel


class CustomerLookupInput(BaseModel):
    customer_id: str


class CustomerEmailLookupInput(BaseModel):
    email: str


class CustomerLookupOutput(BaseModel):
    customer: Customer


class CustomerLookupTool(Tool):
    name = "customer_lookup"
    description = "Fetch safe synthetic customer details by customer id."
    input_model = CustomerLookupInput
    output_model = CustomerLookupOutput
    risk_level = ToolRiskLevel.READ_ONLY

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            output = self.output_model(customer=self.service.get_customer(data.customer_id))
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))


class CustomerLookupByEmailTool(Tool):
    name = "customer_lookup_by_email"
    description = "Fetch safe synthetic customer details by example.test email."
    input_model = CustomerEmailLookupInput
    output_model = CustomerLookupOutput
    risk_level = ToolRiskLevel.READ_ONLY

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            output = self.output_model(customer=self.service.get_customer_by_email(data.email))
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))
