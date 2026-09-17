from pydantic import BaseModel, Field

from app.agent.models import AgentRequest
from app.agent.state import AgentState
from app.core.config import Settings
from app.tools.models import ToolCall, ToolResult
from app.tools.registry import ToolRegistry


class AgentContext(BaseModel):
    request: AgentRequest
    status: str
    step_count: int
    recent_messages: list[dict[str, str]] = Field(default_factory=list)
    tool_calls: list[dict[str, object]] = Field(default_factory=list)
    tool_results: list[dict[str, object]] = Field(default_factory=list)
    available_tools: list[dict[str, object]] = Field(default_factory=list)


def build_agent_context(
    state: AgentState,
    registry: ToolRegistry,
    tool_calls: list[ToolCall],
    tool_results: list[ToolResult],
    settings: Settings,
) -> AgentContext:
    context = AgentContext(
        request=state.request,
        status=state.status.value,
        step_count=state.step_count,
        recent_messages=[
            {"role": message.role.value, "content": message.content}
            for message in state.messages[-12:]
        ],
        tool_calls=[call.model_dump(mode="json") for call in tool_calls[-12:]],
        tool_results=[result.model_dump(mode="json") for result in tool_results[-12:]],
        available_tools=[
            schema.model_dump(mode="json") for schema in registry.schemas()
        ],
    )
    return truncate_context(context, settings.agent_max_context_chars)


def truncate_context(context: AgentContext, max_chars: int) -> AgentContext:
    serialized = context.model_dump_json()
    if len(serialized) <= max_chars:
        return context

    trimmed = context.model_copy(deep=True)
    while len(trimmed.model_dump_json()) > max_chars and trimmed.tool_results:
        trimmed.tool_results.pop(0)
    while len(trimmed.model_dump_json()) > max_chars and trimmed.tool_calls:
        trimmed.tool_calls.pop(0)
    while len(trimmed.model_dump_json()) > max_chars and len(trimmed.recent_messages) > 1:
        trimmed.recent_messages.pop(1)
    return trimmed
