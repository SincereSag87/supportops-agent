from decimal import Decimal

import pytest

from app.agent.decisions import AgentDecision, AgentDecisionType
from app.agent.models import AgentRequest, AgentStatus
from app.agent.parsers import AgentDecisionParseError, parse_agent_decision
from app.agent.prompts import SYSTEM_PROMPT, build_agent_messages
from app.agent.runner import AgentRunner
from app.agent.safety import AgentSafetyController, SafetyAction
from app.agent.state import AgentState
from app.core.config import Settings
from app.llm.base import LLMProviderError
from app.llm.models import ChatMessage, ChatResponse
from app.services.agent_service import AgentService
from app.support.service import create_demo_support_service
from app.tools.models import ToolRiskLevel
from app.tools.support_registry import create_support_tool_registry


class ScriptedProvider:
    def __init__(self, responses: list[str], error: Exception | None = None) -> None:
        self.responses = responses
        self.error = error
        self.calls: list[dict[str, object]] = []

    def generate(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse:
        self.calls.append({"messages": messages, "model": model})
        if self.error:
            raise self.error
        if not self.responses:
            raise RuntimeError("No scripted response remaining")
        return ChatResponse(
            content=self.responses.pop(0),
            model=model or "test",
            provider="scripted",
        )


def decision_json(**kwargs) -> str:
    import json

    return json.dumps(kwargs)


def make_runner(
    responses: list[str],
    settings: Settings | None = None,
    service=None,
    provider: ScriptedProvider | None = None,
) -> tuple[AgentRunner, object, ScriptedProvider]:
    demo_service = service or create_demo_support_service()
    scripted = provider or ScriptedProvider(responses)
    config = settings or Settings(_env_file=None)
    runner = AgentRunner(
        llm_provider=scripted,
        tool_registry=create_support_tool_registry(demo_service),
        safety_controller=AgentSafetyController(config),
        settings=config,
    )
    return runner, demo_service, scripted


def test_decision_models_validate_shapes() -> None:
    tool_call = AgentDecision(
        decision_type=AgentDecisionType.TOOL_CALL,
        reasoning_summary="Need order.",
        tool_name="order_lookup",
        tool_arguments={"order_id": "ORD-1001"},
    )
    final = AgentDecision(
        decision_type=AgentDecisionType.FINAL_RESPONSE,
        reasoning_summary="Enough information.",
        final_response="Delivered.",
    )
    escalation = AgentDecision(
        decision_type=AgentDecisionType.ESCALATE,
        reasoning_summary="Missing data.",
        escalation_reason="Order not found.",
    )
    failure = AgentDecision(
        decision_type=AgentDecisionType.FAIL,
        reasoning_summary="Malformed state.",
        final_response="I could not complete the request.",
    )

    assert tool_call.tool_name == "order_lookup"
    assert final.decision_type == AgentDecisionType.FINAL_RESPONSE
    assert escalation.escalation_reason == "Order not found."
    assert failure.decision_type == AgentDecisionType.FAIL
    with pytest.raises(ValueError):
        AgentDecision(decision_type=AgentDecisionType.TOOL_CALL, reasoning_summary="Bad")


def test_parser_valid_json_fenced_json_and_errors() -> None:
    valid = parse_agent_decision(
        decision_json(
            decision_type="tool_call",
            reasoning_summary="Need customer.",
            tool_name="customer_lookup",
            tool_arguments={"customer_id": "CUS-1001"},
        )
    )
    fenced = parse_agent_decision(
        "```json\n"
        + decision_json(
            decision_type="final_response",
            reasoning_summary="Done.",
            final_response="Delivered.",
        )
        + "\n```"
    )

    assert valid.tool_name == "customer_lookup"
    assert fenced.final_response == "Delivered."
    with pytest.raises(AgentDecisionParseError):
        parse_agent_decision("{bad json")
    with pytest.raises(AgentDecisionParseError):
        parse_agent_decision(decision_json(decision_type="unknown", reasoning_summary="Nope."))
    with pytest.raises(AgentDecisionParseError):
        parse_agent_decision(decision_json(decision_type="tool_call", reasoning_summary="No tool."))
    with pytest.raises(AgentDecisionParseError):
        parse_agent_decision(
            decision_json(decision_type="final_response", reasoning_summary="No final.")
        )


def test_prompts_include_request_tools_safety_json_and_no_private_cot() -> None:
    service = create_demo_support_service()
    registry = create_support_tool_registry(service)
    state = AgentState(
        request=AgentRequest(user_input="Where is ORD-1001?", customer_id="CUS-1001")
    )
    from app.agent.context import build_agent_context

    context = build_agent_context(state, registry, [], [], Settings(_env_file=None))
    messages = build_agent_messages(context)
    joined = "\n".join(message.content for message in messages)

    assert "Where is ORD-1001?" in joined
    assert "order_lookup" in joined
    assert "HIGH_RISK_WRITE tools require approval" in joined
    assert "Return structured JSON only" in joined
    assert "short decision rationale" in joined
    assert "Never output private internal chain-of-thought" in joined
    assert "issue_refund" in joined
    assert "class" not in joined
    assert SYSTEM_PROMPT in messages[0].content


def test_safety_controller_rules() -> None:
    service = create_demo_support_service()
    registry = create_support_tool_registry(service)
    enabled = AgentSafetyController(Settings(_env_file=None))
    disabled = AgentSafetyController(
        Settings(AGENT_ALLOW_LOW_RISK_WRITES=False, _env_file=None)
    )

    assert enabled.evaluate(registry.get("order_lookup"), {"order_id": "ORD-1001"}).action == (
        SafetyAction.EXECUTE
    )
    assert enabled.evaluate(registry.get("create_ticket"), {"customer_id": "CUS-1001"}).action == (
        SafetyAction.EXECUTE
    )
    blocked_low = disabled.evaluate(registry.get("create_ticket"), {"customer_id": "CUS-1001"})
    assert blocked_low.requires_approval is True
    high = enabled.evaluate(
        registry.get("issue_refund"),
        {"order_id": "ORD-1001", "amount": Decimal("10.00"), "reason": "damaged"},
    )
    assert high.action == SafetyAction.REQUIRE_APPROVAL
    assert high.proposed_action is not None
    assert high.proposed_action.estimated_value == Decimal("10.00")


def test_runner_read_tool_observation_then_final_response() -> None:
    runner, _service, _provider = make_runner(
        [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Order status requires order lookup.",
                tool_name="order_lookup",
                tool_arguments={"order_id": "ORD-1001"},
            ),
            decision_json(
                decision_type="final_response",
                reasoning_summary="Order data was retrieved.",
                final_response="ORD-1001 was delivered.",
            ),
        ]
    )

    result = runner.run(AgentRequest(user_input="What is the status of ORD-1001?"))

    assert result.status == AgentStatus.COMPLETED
    assert result.tool_calls[0].tool_name == "order_lookup"
    assert result.tool_results[0].success is True
    assert "delivered" in result.response.lower()


def test_runner_multi_step_high_risk_stops_and_refund_not_executed() -> None:
    service = create_demo_support_service()
    runner, service, _provider = make_runner(
        [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Need customer context.",
                tool_name="customer_lookup",
                tool_arguments={"customer_id": "CUS-1001"},
            ),
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Need order data.",
                tool_name="order_lookup",
                tool_arguments={"order_id": "ORD-1001"},
            ),
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Need refund policy before proposing refund.",
                tool_name="refund_policy_lookup",
                tool_arguments={},
            ),
            decision_json(
                decision_type="tool_call",
                reasoning_summary="A refund can be proposed but requires approval.",
                tool_name="issue_refund",
                tool_arguments={
                    "order_id": "ORD-1001",
                    "amount": "79.99",
                    "reason": "damaged",
                    "idempotency_key": "agent-refund",
                },
            ),
        ],
        service=service,
    )

    result = runner.run(
        AgentRequest(user_input="My headphones arrived damaged.", customer_id="CUS-1001")
    )

    assert result.status == AgentStatus.AWAITING_APPROVAL
    assert result.approvals_required
    assert result.approvals_required[0].action.tool_name == "issue_refund"
    assert result.approvals_required[0].action.risk_level == ToolRiskLevel.HIGH_RISK_WRITE
    assert service.get_order("ORD-1001").refund_total == Decimal("0.00")
    assert all(call.tool_name != "reverse_refund" for call in result.tool_calls)


def test_runner_low_risk_write_execution() -> None:
    runner, _service, _provider = make_runner(
        [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Create a ticket for the damaged item.",
                tool_name="create_ticket",
                tool_arguments={
                    "customer_id": "CUS-1001",
                    "order_id": "ORD-1001",
                    "subject": "Damaged headphones",
                    "description": "Customer reports damaged headphones.",
                    "priority": "normal",
                },
            ),
            decision_json(
                decision_type="final_response",
                reasoning_summary="Ticket creation succeeded.",
                final_response="I opened a support ticket for the damaged headphones.",
            ),
        ]
    )

    result = runner.run(
        AgentRequest(user_input="Please open a support ticket.", customer_id="CUS-1001")
    )

    assert result.status == AgentStatus.COMPLETED
    assert result.tool_calls[0].tool_name == "create_ticket"
    assert result.tool_results[0].success is True


def test_runner_escalate_fail_max_steps_model_failure_and_malformed() -> None:
    escalate_runner, _, _ = make_runner(
        [
            decision_json(
                decision_type="escalate",
                reasoning_summary="The order id is missing.",
                escalation_reason="Need an order id.",
            )
        ]
    )
    fail_runner, _, _ = make_runner(
        [
            decision_json(
                decision_type="fail",
                reasoning_summary="Cannot continue.",
                final_response="I could not complete the request.",
            )
        ]
    )
    max_runner, _, _ = make_runner(
        [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Loop once.",
                tool_name="customer_lookup",
                tool_arguments={"customer_id": "CUS-1001"},
            )
        ],
        settings=Settings(AGENT_MAX_STEPS=1, _env_file=None),
    )
    malformed_runner, _, _ = make_runner(["not json"])
    error_provider = ScriptedProvider([], error=LLMProviderError("offline"))
    model_error_runner, _, _ = make_runner([], provider=error_provider)

    assert escalate_runner.run(AgentRequest(user_input="Help")).status == AgentStatus.ESCALATED
    assert fail_runner.run(AgentRequest(user_input="Help")).status == AgentStatus.FAILED
    assert max_runner.run(AgentRequest(user_input="Help")).status == AgentStatus.ESCALATED
    assert malformed_runner.run(AgentRequest(user_input="Help")).status == AgentStatus.FAILED
    assert model_error_runner.run(AgentRequest(user_input="Help")).status == AgentStatus.FAILED


def test_runner_tool_failure_unknown_invalid_and_duplicate_guard() -> None:
    unknown_runner, _, _ = make_runner(
        [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Try unknown.",
                tool_name="missing_tool",
                tool_arguments={},
            ),
            decision_json(
                decision_type="final_response",
                reasoning_summary="Unknown tool observed.",
                final_response="I could not use that tool.",
            ),
        ]
    )
    invalid_runner, _, _ = make_runner(
        [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Bad args.",
                tool_name="order_lookup",
                tool_arguments={},
            ),
            decision_json(
                decision_type="final_response",
                reasoning_summary="Invalid args observed.",
                final_response="I need an order id.",
            ),
        ]
    )
    duplicate_runner, _, _ = make_runner(
        [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Lookup.",
                tool_name="order_lookup",
                tool_arguments={"order_id": "ORD-1001"},
            ),
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Lookup again.",
                tool_name="order_lookup",
                tool_arguments={"order_id": "ORD-1001"},
            ),
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Lookup again.",
                tool_name="order_lookup",
                tool_arguments={"order_id": "ORD-1001"},
            ),
        ],
        settings=Settings(AGENT_MAX_STEPS=5, AGENT_MAX_IDENTICAL_TOOL_CALLS=2, _env_file=None),
    )

    assert unknown_runner.run(AgentRequest(user_input="Help")).tool_results[0].success is False
    assert invalid_runner.run(AgentRequest(user_input="Help")).tool_results[0].success is False
    duplicate_result = duplicate_runner.run(AgentRequest(user_input="Help"))
    assert duplicate_result.status == AgentStatus.ESCALATED
    assert "Repeated identical" in duplicate_result.response


def test_agent_service_constructs_request_and_propagates_model_and_customer() -> None:
    runner, _service, provider = make_runner(
        [
            decision_json(
                decision_type="final_response",
                reasoning_summary="Answer directly.",
                final_response="Done.",
            )
        ]
    )
    result = AgentService(runner).handle_request("Hello", customer_id="CUS-1001", model="gemma3")

    assert result.status == AgentStatus.COMPLETED
    assert provider.calls[0]["model"] == "gemma3"
