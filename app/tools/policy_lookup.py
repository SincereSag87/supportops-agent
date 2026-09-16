from uuid import uuid4

from pydantic import BaseModel

from app.domain.policies import RefundPolicy
from app.support.service import SupportService
from app.tools.base import Tool
from app.tools.models import ToolResult, ToolRiskLevel


class RefundPolicyLookupInput(BaseModel):
    policy_type: str = "refund"


class RefundPolicyLookupOutput(BaseModel):
    policy: RefundPolicy


class RefundPolicyLookupTool(Tool):
    name = "refund_policy_lookup"
    description = "Return the current synthetic refund policy."
    input_model = RefundPolicyLookupInput
    output_model = RefundPolicyLookupOutput
    risk_level = ToolRiskLevel.READ_ONLY

    def __init__(self, service: SupportService) -> None:
        self.service = service

    def execute(self, tool_input: BaseModel) -> ToolResult:
        self.input_model.model_validate(tool_input)
        output = self.output_model(policy=self.service.get_refund_policy())
        return ToolResult(call_id=uuid4(), tool_name=self.name, success=True, output=output)
