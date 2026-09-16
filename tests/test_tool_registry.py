import pytest

from app.tools.demo import EchoTool, EchoToolInput
from app.tools.models import ToolRiskLevel
from app.tools.registry import DuplicateToolError, ToolRegistry, UnknownToolError


def test_tool_metadata_and_execution_contract() -> None:
    tool = EchoTool()

    result = tool.execute(EchoToolInput(message="hello"))

    assert tool.name == "echo"
    assert tool.risk_level == ToolRiskLevel.READ_ONLY
    assert result.success is True
    assert result.output is not None
    assert result.output.model_dump()["message"] == "hello"


def test_tool_registry_register_lookup_list_and_contains() -> None:
    registry = ToolRegistry()
    tool = EchoTool()

    registry.register(tool)

    assert registry.get("echo") is tool
    assert registry.list_tools() == [tool]
    assert registry.contains("echo") is True


def test_tool_registry_duplicate_prevention() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    with pytest.raises(DuplicateToolError):
        registry.register(EchoTool())


def test_tool_registry_unknown_tool() -> None:
    registry = ToolRegistry()

    with pytest.raises(UnknownToolError):
        registry.get("missing")


def test_tool_schema_generation() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    schema = registry.schemas()[0]

    assert schema.name == "echo"
    assert schema.risk_level == ToolRiskLevel.READ_ONLY
    assert "properties" in schema.input_schema
    assert "message" in schema.input_schema["properties"]
