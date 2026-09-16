from uuid import uuid4

from pydantic import BaseModel

from app.domain.tickets import SupportTicket, TicketPriority, TicketStatus
from app.repositories.base import SupportDomainError
from app.support.service import SupportService
from app.tools.base import Tool
from app.tools.models import ToolResult, ToolRiskLevel


class TicketLookupInput(BaseModel):
    ticket_id: str


class CreateTicketInput(BaseModel):
    customer_id: str
    order_id: str | None = None
    subject: str
    description: str
    priority: TicketPriority = TicketPriority.NORMAL


class UpdateTicketStatusInput(BaseModel):
    ticket_id: str
    status: TicketStatus
    resolution: str | None = None


class TicketOutput(BaseModel):
    ticket: SupportTicket


class TicketLookupTool(Tool):
    name = "ticket_lookup"
    description = "Fetch a synthetic support ticket by id."
    input_model = TicketLookupInput
    output_model = TicketOutput
    risk_level = ToolRiskLevel.READ_ONLY

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            output = self.output_model(ticket=self.service.get_ticket(data.ticket_id))
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))


class CreateTicketTool(Tool):
    name = "create_ticket"
    description = "Create a synthetic support ticket."
    input_model = CreateTicketInput
    output_model = TicketOutput
    risk_level = ToolRiskLevel.LOW_RISK_WRITE

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            output = self.output_model(
                ticket=self.service.create_ticket(
                    customer_id=data.customer_id,
                    order_id=data.order_id,
                    subject=data.subject,
                    description=data.description,
                    priority=data.priority,
                )
            )
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))


class UpdateTicketStatusTool(Tool):
    name = "update_ticket_status"
    description = "Update a synthetic support ticket status."
    input_model = UpdateTicketStatusInput
    output_model = TicketOutput
    risk_level = ToolRiskLevel.LOW_RISK_WRITE

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            output = self.output_model(
                ticket=self.service.update_ticket_status(
                    ticket_id=data.ticket_id,
                    status=data.status,
                    resolution=data.resolution,
                )
            )
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))
