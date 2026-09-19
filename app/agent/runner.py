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
from app.audit.models import AuditEventType
from app.audit.service import AuditService
from app.core.config import Settings
from app.llm.base import LLMProvider, LLMProviderError
from app.policies.engine import PolicyEngine
from app.policies.models import ApprovalRequest, PolicyDecision
from app.services.action_service import ActionExecutionError, ActionNotAllowedError, ActionService
from app.tools.models import ToolCall, ToolResult
from app.tools.registry import ToolRegistry, UnknownToolError


class AgentRunner:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        safety_controller: AgentSafetyController,
        settings: Settings,
        policy_engine: PolicyEngine | None = None,
        action_service: ActionService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.safety_controller = safety_controller
        self.settings = settings
        self.policy_engine = policy_engine
        self.action_service = action_service
        self.audit_service = audit_service

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
        self._audit(request.request_id, AuditEventType.REQUEST_RECEIVED, "agent", success=True)

        for step in range(1, self.settings.agent_max_steps + 1):
            state.status = AgentStatus.REASONING
            context = build_agent_context(
                state, self.tool_registry, tool_calls, tool_results, self.settings
            )
            try:
                messages = build_agent_messages(context)
                response = self.llm_provider.generate(messages, model=model)
                self._audit(request.request_id, AuditEventType.MODEL_CALLED, "agent", success=True)
                try:
                    decision = parse_agent_decision(response.content)
                except AgentDecisionParseError:
                    decision = self._repair_decision(messages, response.content, model)
            except (LLMProviderError, AgentDecisionParseError) as exc:
                state.status = AgentStatus.FAILED
                self._audit(
                    request.request_id,
                    AuditEventType.REQUEST_FAILED,
                    "agent",
                    details={"error": str(exc)},
                    success=False,
                )
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
                    result.get("approval")
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
            if state.status == AgentStatus.FAILED:
                return self._result(
                    state,
                    response=result["trace"].observation or "The action was blocked.",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    decisions=decisions,
                    error=result["trace"].observation,
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
    ) -> dict[str, object]:
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
        self._audit(
            state.request.request_id,
            AuditEventType.TOOL_SELECTED,
            "agent",
            tool_name=tool.name,
            details={"risk_level": tool.risk_level.value},
            success=True,
        )
        if safety.action != SafetyAction.EXECUTE:
            return self._handle_blocked_action(state, safety, trace, tool_calls, tool_results)

        state.status = AgentStatus.EXECUTING
        try:
            self._audit(
                state.request.request_id,
                AuditEventType.TOOL_STARTED,
                "agent",
                tool_name=tool.name,
                success=None,
            )
            result = tool.execute(validated_input)
        except Exception:
            result = self._failure_result(tool.name, "Tool execution failed safely.")
        self._audit(
            state.request.request_id,
            AuditEventType.TOOL_COMPLETED if result.success else AuditEventType.TOOL_FAILED,
            "agent",
            tool_name=tool.name,
            details={"success": result.success, "error": result.error},
            success=result.success,
        )
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

    def _handle_blocked_action(
        self,
        state: AgentState,
        safety,
        trace: AgentDecisionTrace,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
    ) -> dict[str, object]:
        action = safety.proposed_action
        if action is None:
            state.status = AgentStatus.AWAITING_APPROVAL
            trace.tool_success = None
            trace.observation = safety.reason
            return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

        if self.policy_engine is None or self.action_service is None:
            approval = ApprovalRequest(
                request_id=state.request.request_id,
                action=action,
                reason=safety.reason,
            )
            state.status = AgentStatus.AWAITING_APPROVAL
            state.pending_action = action
            trace.tool_success = None
            trace.observation = safety.reason
            return {
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "trace": trace,
                "approval": approval,
            }

        context = self.policy_engine.build_context(action, customer_id=state.request.customer_id)
        policy_result = self.policy_engine.evaluate(action, context)
        self._audit(
            state.request.request_id,
            AuditEventType.POLICY_CHECKED,
            "policy_engine",
            tool_name=action.tool_name,
            details={
                "decision": policy_result.decision.value,
                "reason": policy_result.reason,
            },
            success=True,
        )
        if policy_result.decision == PolicyDecision.ALLOW:
            try:
                result = self.action_service.execute(
                    state.request.request_id,
                    action,
                    policy_result,
                    approval_id=None,
                )
            except (ActionNotAllowedError, ActionExecutionError) as exc:
                state.status = AgentStatus.FAILED
                trace.tool_success = False
                trace.observation = str(exc)
                return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}
            tool_results.append(result)
            trace.tool_success = result.success
            trace.observation = "policy allowed and action executed"
            state.messages.append(
                AgentMessage(role=AgentMessageRole.TOOL, content=result.model_dump_json())
            )
            return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

        if policy_result.decision == PolicyDecision.REQUIRE_APPROVAL:
            approval = None
            if self.action_service:
                approval = self.action_service.approval_service.create_request(
                    request_id=state.request.request_id,
                    action=action,
                    reason=policy_result.reason,
                    policy_decision=policy_result,
                )
                self._audit(
                    state.request.request_id,
                    AuditEventType.APPROVAL_REQUESTED,
                    "approval_service",
                    tool_name=action.tool_name,
                    details={"approval_id": str(approval.approval_id)},
                    success=True,
                )
            state.status = AgentStatus.AWAITING_APPROVAL
            state.pending_action = action
            trace.tool_success = None
            trace.observation = policy_result.reason
            return {
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "trace": trace,
                "approval": approval,
            }

        if policy_result.decision == PolicyDecision.DENY:
            state.status = AgentStatus.FAILED
            self._audit(
                state.request.request_id,
                AuditEventType.ACTION_BLOCKED,
                "policy_engine",
                tool_name=action.tool_name,
                details={"reason": policy_result.reason},
                success=True,
            )
            trace.tool_success = False
            trace.observation = policy_result.reason
            return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

        state.status = AgentStatus.ESCALATED
        self._audit(
            state.request.request_id,
            AuditEventType.ESCALATED,
            "policy_engine",
            tool_name=action.tool_name,
            details={"reason": policy_result.reason},
            success=True,
        )
        trace.tool_success = None
        trace.observation = policy_result.reason
        return {"tool_calls": tool_calls, "tool_results": tool_results, "trace": trace}

    def _failure_result(self, tool_name: str, error: str) -> ToolResult:
        return ToolResult(call_id=uuid4(), tool_name=tool_name, success=False, error=error)

    def _repair_decision(
        self,
        messages,
        invalid_content: str,
        model: str | None,
    ) -> AgentDecision:
        last_error: AgentDecisionParseError | None = None
        repair_messages = [
            *messages,
            AgentMessage(
                role=AgentMessageRole.SYSTEM,
                content=(
                    "The previous response was invalid. Return only valid JSON matching the "
                    "AgentDecision schema. Do not include markdown or explanations."
                ),
            ),
            AgentMessage(role=AgentMessageRole.USER, content=invalid_content[:2000]),
        ]
        for _ in range(self.settings.agent_decision_repair_attempts):
            try:
                response = self.llm_provider.generate(repair_messages, model=model)
            except Exception as exc:
                raise AgentDecisionParseError("LLM decision repair failed") from exc
            try:
                return parse_agent_decision(response.content)
            except AgentDecisionParseError as exc:
                last_error = exc
        raise last_error or AgentDecisionParseError("LLM output was not valid JSON")

    def _audit(
        self,
        request_id,
        event_type: AuditEventType,
        actor: str,
        tool_name: str | None = None,
        details: dict | None = None,
        success: bool | None = None,
    ) -> None:
        if self.audit_service is not None:
            self.audit_service.record(
                request_id=request_id,
                event_type=event_type,
                actor=actor,
                tool_name=tool_name,
                details=details,
                success=success,
            )

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
