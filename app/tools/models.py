from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolRiskLevel(StrEnum):
    READ_ONLY = "read_only"
    LOW_RISK_WRITE = "low_risk_write"
    HIGH_RISK_WRITE = "high_risk_write"


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, str | int | bool] = Field(default_factory=dict)
    call_id: UUID = Field(default_factory=uuid4)


class ToolResult(BaseModel):
    call_id: UUID
    tool_name: str
    success: bool
    output: BaseModel | None = None
    error: str | None = None
    reversible: bool = False
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)


class ToolSchema(BaseModel):
    name: str
    description: str
    input_schema: dict[str, object]
    risk_level: ToolRiskLevel
