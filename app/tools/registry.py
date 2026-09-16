from app.tools.base import Tool
from app.tools.models import ToolSchema


class ToolRegistryError(RuntimeError):
    """Base registry error."""


class DuplicateToolError(ToolRegistryError):
    """Raised when a tool name is registered more than once."""


class UnknownToolError(ToolRegistryError):
    """Raised when a requested tool is not registered."""


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool, *, allow_replace: bool = False) -> None:
        if tool.name in self._tools and not allow_replace:
            raise DuplicateToolError(f"Tool is already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(f"Unknown tool: {name}") from exc

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def contains(self, name: str) -> bool:
        return name in self._tools

    def schemas(self) -> list[ToolSchema]:
        return [tool.schema() for tool in self.list_tools()]
