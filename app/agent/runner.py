from collections import Counter
from uuid import uuid4

from pydantic import ValidationError

from app.agent.context import build_agent_context
from app.agent.decisions import AgentDecision, AgentDecisionTrace, AgentDecisionType
from app.agent.models import AgentMessage, AgentMessageRole, AgentRequest, AgentStatus
from app.agent.parsers import AgentDecisionParseError, parse_agent_decision
from app.agent.prompts import build_agent_messages
from app.agent.results import AgentResult
from app.agent.safety import AgentSafetyController, SafetyAction
from app.agent.state import AgentState
from app.core.config import Settings
from app.llm.base import LLMProvider, LLMProviderError
from app.policies.models import ApprovalRequest
from app.tools.models import ToolCall, ToolResult
from app.tools.registry import ToolRegistry, UnknownToolError


class AgentRunner:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        safety_controller: AgentSafetyController,
        settings: Settings,
    ) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.safety_controller = safety_controller
        self.settings = settings

    def run(self, request: AgentRequest, model: str | None = None) -> AgentResult:
        state = AgentState(
            request=request,
            status=AgentStatus.RECEIVED,
            messages=[
                AgentMessage(role=AgentMessageRole.USER, content=request.user_input),
            ],
        )
        tool_calls: list[ToolCall] = []
        tool_results: list[ToolResult] = []
        decisions: list[AgentDecision] = []
        traces: list[AgentDecisionTrace] = []
        duplicate_counter: Counter[str] = Counter()

        for step in range(1, self.settings.agent_max_steps + 1):
            state.status = AgentStatus.REASONING
            context = build_agent_context(
                state, self.tool_registry, tool_calls, tool_results, self.settings
            )
            try:
                response = self.llm_provider.generate(build_agent_messages(context), model=model)
                decision = parse_agent_decision(response.content)
            except (LLMProviderError, AgentDecisionParseError) as exc:
                state.status = AgentStatus.FAILED
                return self._result(
                    state,
                    response="The agent could not produce a valid next decision.",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    decisions=decisions,
                    error=str(exc),
                )

            decisions.append(decision)
            state.step_count = step
            state.messages.append(
                AgentMessage(role=AgentMessageRole.AGENT, content=decision.reasoning_summary)
            )

            if decision.decision_type == AgentDecisionType.FINAL_RESPONSE:
                state.status = AgentStatus.COMPLETED
                state.messages.append(
                    AgentMessage(
                        role=AgentMessageRole.AGENT,
                        content=decision.final_response or "",
                    )
                )
                return self._result(
                    state,
                    response=decision.final_response or "",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    decisions=decisions,
                )

            if decision.decision_type == AgentDecisionType.ESCALATE:
                state.status = AgentStatus.ESCALATED
                return self._result(
                    state,
                    response=decision.escalation_reason or "Escalation required.",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    decisions=decisions,
                    escalated=True,
                )

            if decision.decision_type == AgentDecisionType.FAIL:
                state.status = AgentStatus.FAILED
                return self._result(
                    state,
                    response=decision.final_response or "The agent failed safely.",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    decisions=decisions,
                    error=decision.final_response,
                )

            result = self._handle_tool_call(decision, state, duplicate_counter)
            tool_calls.extend(result["tool_calls"])
            tool_results.extend(result["tool_results"])
            traces.append(result["trace"])
            if state.status == AgentStatus.AWAITING_APPROVAL:
                proposed_action = state.pending_action
                approval = (
                    ApprovalRequest(
                        request_id=request.request_id,
                        action=proposed_action,
                        reason="Runtime approval required before high-risk execution.",
                    )
                    if proposed_action
                    else None
                )
                return self._result(
                    state,
                    response="Approval is required before executing the proposed action.",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    decisions=decisions,
                    approvals=[approval] if approval else [],
                )
            if state.status == AgentStatus.ESCALATED:
                return self._result(
                    state,
                    response=result["trace"].observation or "Escalation required.",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    decisions=decisions,
                    escalated=True,
                )

        state.status = AgentStatus.ESCALATED
        return self._result(
            state,
            response="Agent reached the maximum number of allowed steps.",
            tool_calls=tool_calls,
            tool_results=tool_results,
            decisions=decisions,
            escalated=True,
        )

    def _handle_tool_call(
        self,
        decision: AgentDecision,
        state: AgentState,
        duplicate_counter: Counter[str],
    ) -> dict[str, list[ToolCall] | list[ToolResult] | AgentDecisionTrace]:
        assert decision.tool_name is not None
        tool_calls: list[ToolCall] = []
        tool_results: list[ToolResult] = []
        trace = AgentDecisionTrace(
            step=state.step_count,
            decision_type=decision.decision_type,
            reasoning_summary=decision.reasoning_summary,
            tool_name=decision.tool_name,
        )
        try:
            tool = self.tool_registry.get(decision.tool_name)
        except UnknownToolError as exc:
            tool_results.append(self._failure_result(decision.tool_name, str(exc)))
            trace.tool_success = False
            trace.observation = str(exc)
            state.messages.append(AgentMessage(role=AgentMessageRole.TOOL, content=str(exc)))
            return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

        try:
            validated_input = tool.input_model.model_validate(decision.tool_arguments or {})
        except ValidationError as exc:
            message = f"Invalid tool arguments: {exc}"
            tool_results.append(self._failure_result(tool.name, message))
            trace.tool_success = False
            trace.observation = message
            state.messages.append(AgentMessage(role=AgentMessageRole.TOOL, content=message))
            return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

        args = validated_input.model_dump(mode="python")
        duplicate_key = f"{tool.name}:{validated_input.model_dump_json()}"
        duplicate_counter[duplicate_key] += 1
        if duplicate_counter[duplicate_key] > self.settings.agent_max_identical_tool_calls:
            state.status = AgentStatus.ESCALATED
            trace.tool_success = False
            trace.observation = "Repeated identical tool call limit reached."
            return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

        safety = self.safety_controller.evaluate(tool, args)
        call = ToolCall(tool_name=tool.name, arguments=validated_input.model_dump(mode="json"))
        tool_calls.append(call)
        if safety.action != SafetyAction.EXECUTE:
            state.status = AgentStatus.AWAITING_APPROVAL
            state.pending_action = safety.proposed_action
            trace.tool_success = None
            trace.observation = safety.reason
            return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

        state.status = AgentStatus.EXECUTING
        try:
            result = tool.execute(validated_input)
        except Exception:
            result = self._failure_result(tool.name, "Tool execution failed safely.")
        tool_results.append(result)
        trace.tool_success = result.success
        trace.observation = "success" if result.success else result.error
        state.messages.append(
            AgentMessage(
                role=AgentMessageRole.TOOL,
                content=result.model_dump_json(),
            )
        )
        return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

    def _failure_result(self, tool_name: str, error: str) -> ToolResult:
        return ToolResult(call_id=uuid4(), tool_name=tool_name, success=False, error=error)

    def _result(
        self,
        state: AgentState,
        response: str,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
        decisions: list[AgentDecision],
        approvals: list[ApprovalRequest] | None = None,
        escalated: bool = False,
        error: str | None = None,
    ) -> AgentResult:
        return AgentResult(
            request_id=state.request.request_id,
            status=state.status,
            response=response,
            tool_calls=tool_calls,
            tool_results=tool_results,
            decision_history=decisions,
            approvals_required=approvals or [],
            escalated=escalated,
            error=error,
        )
