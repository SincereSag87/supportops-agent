from uuid import uuid4

from pydantic import BaseModel

from app.tools.base import Tool
from app.tools.models import ToolResult, ToolRiskLevel


class EchoToolInput(BaseModel):
    message: str


class EchoToolOutput(BaseModel):
    message: str


class EchoTool(Tool):
    name = "echo"
    description = "Test/demo tool that echoes a supplied message."
    input_model = EchoToolInput
    output_model = EchoToolOutput
    risk_level = ToolRiskLevel.READ_ONLY

    def execute(self, tool_input: BaseModel) -> ToolResult:
        validated = self.input_model.model_validate(tool_input)
        return ToolResult(
            call_id=uuid4(),
            tool_name=self.name,
            success=True,
            output=self.output_model(message=validated.message),
            reversible=False,
        )
