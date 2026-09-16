from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel

from app.domain.refunds import RefundRecord
from app.repositories.base import SupportDomainError
from app.support.service import SupportService
from app.tools.base import Tool
from app.tools.models import ToolResult, ToolRiskLevel


class IssueRefundInput(BaseModel):
    order_id: str
    amount: Decimal
    reason: str
    idempotency_key: str


class ReverseRefundInput(BaseModel):
    refund_id: str
    idempotency_key: str
    reason: str


class RefundOutput(BaseModel):
    refund: RefundRecord
    created: bool
    order_refund_total: str
    order_status: str
    remaining_refundable_amount: str


class IssueRefundTool(Tool):
    name = "issue_refund"
    description = "Issue a controlled synthetic refund with an idempotency key."
    input_model = IssueRefundInput
    output_model = RefundOutput
    risk_level = ToolRiskLevel.HIGH_RISK_WRITE

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            refund, created = self.service.issue_refund(
                order_id=data.order_id,
                amount=data.amount,
                reason=data.reason,
                idempotency_key=data.idempotency_key,
            )
            order = self.service.get_order(data.order_id)
            output = self.output_model(
                refund=refund,
                created=created,
                order_refund_total=str(order.refund_total),
                order_status=order.status.value,
                remaining_refundable_amount=str(order.remaining_refundable_amount),
            )
            return ToolResult(
                call_id=uuid4(),
                tool_name=self.name,
                success=True,
                output=output,
                reversible=True,
                metadata={"idempotent_replay": not created},
            )
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))


class ReverseRefundTool(Tool):
    name = "reverse_refund"
    description = "Create a synthetic reversal record for a completed refund."
    input_model = ReverseRefundInput
    output_model = RefundOutput
    risk_level = ToolRiskLevel.HIGH_RISK_WRITE

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        data = self.input_model.model_validate(tool_input)
        try:
            reversal, created = self.service.reverse_refund(
                refund_id=data.refund_id,
                idempotency_key=data.idempotency_key,
                reason=data.reason,
            )
            order = self.service.get_order(reversal.order_id)
            output = self.output_model(
                refund=reversal,
                created=created,
                order_refund_total=str(order.refund_total),
                order_status=order.status.value,
                remaining_refundable_amount=str(order.remaining_refundable_amount),
            )
            return ToolResult(
                call_id=uuid4(),
                tool_name=self.name,
                success=True,
                output=output,
                reversible=False,
                metadata={"idempotent_replay": not created},
            )
        except SupportDomainError as exc:
            return ToolResult(call_id=uuid4(), tool_name=self.name, success=False, error=str(exc))
