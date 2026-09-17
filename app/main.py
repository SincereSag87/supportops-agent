import argparse
import json
from pathlib import Path

from app.agent.runner import AgentRunner
from app.agent.safety import AgentSafetyController
from app.core.config import get_settings
from app.domain.tickets import TicketStatus
from app.llm.base import LLMProviderError
from app.llm.models import ChatMessage, ChatRole
from app.llm.ollama_provider import OllamaProvider
from app.services.agent_service import AgentService
from app.services.health_service import HealthService
from app.support.service import create_demo_support_service
from app.tools.demo import EchoTool, EchoToolInput
from app.tools.models import ToolRiskLevel
from app.tools.registry import ToolRegistry
from app.tools.support_registry import create_support_tool_registry


def build_registry(include_demo_tools: bool = False) -> ToolRegistry:
    service = create_demo_support_service()
    registry = create_support_tool_registry(service)
    if include_demo_tools:
        registry.register(EchoTool())
    return registry


def print_health(include_demo_tools: bool = False) -> int:
    settings = get_settings()
    registry = build_registry(include_demo_tools=include_demo_tools)
    health = HealthService(settings=settings, tool_registry=registry).check()
    ollama_status = "reachable" if health.ollama_reachable else "unavailable"
    print("SupportOps Agent")
    print(f"Status: {health.status}")
    print(f"Ollama: {ollama_status}")
    print(f"Model: {health.configured_model}")
    print(f"Registered tools: {health.registered_tool_count}")
    return 0


def run_llm_test(model: str | None = None) -> int:
    settings = get_settings()
    provider = OllamaProvider(settings)
    prompt = (
        "Explain in three sentences why an AI agent should require human approval before "
        "high-risk actions."
    )
    try:
        response = provider.generate([ChatMessage(role=ChatRole.USER, content=prompt)], model=model)
    except LLMProviderError as exc:
        print(f"LLM test failed: {exc}")
        return 1
    print(response.content)
    return 0


def list_tools(include_demo_tools: bool = False) -> int:
    registry = build_registry(include_demo_tools=include_demo_tools)
    print("Name\tRisk\tDescription")
    for tool in registry.list_tools():
        print(f"{tool.name}\t{tool.risk_level.value}\t{tool.description}")
    return 0


def run_tool_test(tool_name: str) -> int:
    registry = build_registry(include_demo_tools=True)
    if tool_name != "echo":
        print("Only the explicit test/demo echo tool can be run from this command.")
        return 1
    tool = registry.get(tool_name)
    result = tool.execute(EchoToolInput(message="SupportOps Agent demo tool check"))
    print(result.model_dump_json())
    return 0


def print_customer(customer_id: str) -> int:
    service = create_demo_support_service()
    customer = service.get_customer(customer_id)
    orders = service.get_customer_orders(customer_id)
    open_tickets = [
        ticket
        for ticket in service.get_customer_tickets(customer_id)
        if ticket.status != TicketStatus.CLOSED
    ]
    print("Customer")
    print(f"  ID: {customer.customer_id}")
    print(f"  Name: {customer.name}")
    print(f"  Email: {customer.email}")
    print(f"  Status: {customer.status.value}")
    print("Orders")
    for order in orders:
        print(f"  {order.order_id}: {order.total} {order.currency} ({order.status.value})")
    print("Open tickets")
    for ticket in open_tickets:
        print(f"  {ticket.ticket_id}: {ticket.subject} ({ticket.status.value})")
    return 0


def print_order(order_id: str) -> int:
    service = create_demo_support_service()
    order = service.get_order(order_id)
    print("Order")
    print(f"  ID: {order.order_id}")
    print(f"  Customer: {order.customer_id}")
    print("Items")
    for item in order.items:
        print(f"  {item.quantity} x {item.product_name} @ {item.unit_price}")
    print(f"Total: {order.total} {order.currency}")
    print(f"Status: {order.status.value}")
    print(f"Delivered: {order.delivered_at.date() if order.delivered_at else 'not delivered'}")
    print(f"Refunded: {order.refund_total} {order.currency}")
    print(f"Remaining refundable: {order.remaining_refundable_amount} {order.currency}")
    return 0


def print_refund_policy() -> int:
    policy = create_demo_support_service().get_refund_policy()
    print("Refund Policy")
    print(f"Version: {policy.policy_version}")
    print(f"Return window: {policy.return_window_days} days")
    print(f"Automatic refund threshold: {policy.auto_refund_limit}")
    print(f"Approval threshold: {policy.approval_refund_limit}")
    print(f"Requires delivered order: {policy.requires_delivered_order}")
    print(f"Allowed reasons: {', '.join(policy.allowed_reasons)}")
    return 0


def run_tool_command(
    tool_name: str,
    raw_input: str | None,
    input_file: str | None,
    confirm_write: bool,
) -> int:
    registry = build_registry()
    tool = registry.get(tool_name)
    if tool.risk_level != ToolRiskLevel.READ_ONLY and not confirm_write:
        print("Refusing to execute write tool without --confirm-write.")
        print(f"Tool: {tool.name}")
        print(f"Risk: {tool.risk_level.value}")
        return 1
    try:
        if input_file is not None:
            payload_text = Path(input_file).read_text(encoding="utf-8-sig")
        else:
            payload_text = raw_input or "{}"
        payload = json.loads(payload_text)
        tool_input = tool.input_model.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid tool input: {exc}")
        return 1

    result = tool.execute(tool_input)
    print(result.model_dump_json(indent=2))
    return 0 if result.success else 1


def build_agent_service() -> AgentService:
    settings = get_settings()
    support_service = create_demo_support_service()
    registry = create_support_tool_registry(support_service)
    runner = AgentRunner(
        llm_provider=OllamaProvider(settings),
        tool_registry=registry,
        safety_controller=AgentSafetyController(settings),
        settings=settings,
    )
    return AgentService(runner)


def run_agent_command(
    user_input: str,
    customer_id: str | None,
    model: str | None,
    output: str | None,
    show_trace: bool,
) -> int:
    result = build_agent_service().handle_request(user_input, customer_id=customer_id, model=model)
    if output == "json":
        print(result.model_dump_json(indent=2))
        return 0 if result.error is None else 1

    print(f"Request ID: {result.request_id}")
    print(f"Status: {result.status.value}")
    print(f"Steps: {len(result.decision_history)}")
    print(f"Response: {result.response}")
    print("Tool Calls:")
    for index, call in enumerate(result.tool_calls, start=1):
        print(f"{index}. {call.tool_name} {call.arguments}")
    if result.approvals_required:
        approval = result.approvals_required[0]
        action = approval.action
        print("Pending Action:")
        print(f"Tool: {action.tool_name}")
        print(f"Arguments: {action.arguments}")
        print(f"Risk: {action.risk_level.name}")
        print("Approval Required: Yes")
    if show_trace:
        print("Execution Trace:")
        for index, decision in enumerate(result.decision_history, start=1):
            print(f"Step {index}")
            print(f"Decision: {decision.decision_type.value}")
            print(f"Reason: {decision.reasoning_summary}")
            if decision.tool_name:
                matching = [
                    item for item in result.tool_results if item.tool_name == decision.tool_name
                ]
                success = matching[-1].success if matching else None
                print(f"Tool: {decision.tool_name}")
                print(f"Result: {success if success is not None else 'not executed'}")
    return 0 if result.error is None else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="SupportOps Agent CLI")
    parser.add_argument("--llm-test", action="store_true", help="Run a safe LLM smoke prompt")
    parser.add_argument("--model", help="Override the configured LLM model")
    parser.add_argument("--agent", help="Run the Phase 3 tool-using agent loop")
    parser.add_argument("--customer-id", help="Synthetic customer id for --agent")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--show-trace", action="store_true", help="Show safe execution trace")
    parser.add_argument("--list-tools", action="store_true", help="List registered tools")
    parser.add_argument("--customer", help="Show synthetic customer, orders, and open tickets")
    parser.add_argument("--order", help="Show synthetic order details")
    parser.add_argument("--refund-policy", action="store_true", help="Show synthetic refund policy")
    parser.add_argument("--tool", help="Execute a registered tool with explicit input")
    parser.add_argument("--input", help="JSON input for --tool")
    parser.add_argument("--input-file", help="Path to a JSON input file for --tool")
    parser.add_argument(
        "--confirm-write",
        action="store_true",
        help="Required to execute low-risk or high-risk write tools",
    )
    parser.add_argument(
        "--tool-test",
        choices=["echo"],
        help="Run an explicit demo tool smoke test",
    )
    parser.add_argument(
        "--include-demo-tools",
        action="store_true",
        help="Include internal test/demo tools in registry output",
    )
    args = parser.parse_args()

    if args.agent:
        return run_agent_command(
            user_input=args.agent,
            customer_id=args.customer_id,
            model=args.model,
            output=args.output,
            show_trace=args.show_trace,
        )
    if args.llm_test:
        return run_llm_test(model=args.model)
    if args.list_tools:
        return list_tools(include_demo_tools=args.include_demo_tools)
    if args.customer:
        return print_customer(args.customer)
    if args.order:
        return print_order(args.order)
    if args.refund_policy:
        return print_refund_policy()
    if args.tool:
        return run_tool_command(args.tool, args.input, args.input_file, args.confirm_write)
    if args.tool_test:
        return run_tool_test(args.tool_test)
    return print_health(include_demo_tools=args.include_demo_tools)


if __name__ == "__main__":
    raise SystemExit(main())
