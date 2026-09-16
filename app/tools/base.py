from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.tools.models import ToolResult, ToolRiskLevel, ToolSchema


class Tool(ABC):
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    risk_level: ToolRiskLevel

    @abstractmethod
    def execute(self, tool_input: BaseModel) -> ToolResult:
        """Execute the tool against already validated input."""

    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            input_schema=self.input_model.model_json_schema(),
            risk_level=self.risk_level,
        )
