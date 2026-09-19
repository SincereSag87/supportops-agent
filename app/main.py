import argparse
import json
from pathlib import Path
from uuid import UUID

from app.agent.runner import AgentRunner
from app.agent.safety import AgentSafetyController
from app.approvals.repository import InMemoryApprovalRepository
from app.approvals.service import ApprovalService
from app.audit.repository import InMemoryAuditRepository
from app.audit.service import AuditService
from app.core.config import get_settings
from app.domain.tickets import TicketStatus
from app.evaluation.formatter import format_report
from app.evaluation.models import EvaluationMode
from app.llm.base import LLMProviderError
from app.llm.models import ChatMessage, ChatRole
from app.llm.ollama_provider import OllamaProvider
from app.policies.engine import PolicyEngine
from app.policies.models import ProposedAction
from app.services.action_service import ActionService
from app.services.agent_service import AgentService
from app.services.evaluation_service import EvaluationService
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
    approval_service = ApprovalService(InMemoryApprovalRepository())
    audit_service = AuditService(InMemoryAuditRepository())
    action_service = ActionService(registry, approval_service, audit_service)
    policy_engine = PolicyEngine(support_service)
    runner = AgentRunner(
        llm_provider=OllamaProvider(settings),
        tool_registry=registry,
        safety_controller=AgentSafetyController(settings),
        settings=settings,
        policy_engine=policy_engine,
        action_service=action_service,
        audit_service=audit_service,
    )
    return AgentService(
        runner,
        approval_service=approval_service,
        action_service=action_service,
        audit_service=audit_service,
    )


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


def print_pending_approvals() -> int:
    service = build_agent_service()
    approvals = service.approval_service.list_pending() if service.approval_service else []
    print("Approval ID\tRequest ID\tTool\tAmount\tReason\tStatus")
    for approval in approvals:
        print(
            f"{approval.approval_id}\t{approval.request_id}\t{approval.action.tool_name}\t"
            f"{approval.action.arguments.get('amount', '')}\t{approval.reason}\t"
            f"{approval.status.value}"
        )
    return 0


def resolve_approval_command(
    approval_id: str,
    approved: bool,
    actor: str,
    comment: str | None,
) -> int:
    try:
        result = build_agent_service().resolve_approval(
            UUID(approval_id),
            approved=approved,
            decided_by=actor,
            comment=comment,
        )
    except Exception as exc:
        print(f"Approval resolution failed: {exc}")
        return 1
    print(result.model_dump_json(indent=2))
    return 0 if result.error is None else 1


def demo_approval_flow(approve_demo: bool) -> int:
    support_service = create_demo_support_service()
    registry = create_support_tool_registry(support_service)
    approval_service = ApprovalService(InMemoryApprovalRepository())
    audit_service = AuditService(InMemoryAuditRepository())
    action_service = ActionService(registry, approval_service, audit_service)
    policy_engine = PolicyEngine(support_service)
    request_id = UUID("00000000-0000-4000-8000-000000000004")
    action = ProposedAction(
        action_type="issue_refund",
        tool_name="issue_refund",
        arguments={
            "order_id": "ORD-1002",
            "amount": "299.99",
            "reason": "defective",
            "idempotency_key": "phase4-demo-approval",
        },
        risk_level=ToolRiskLevel.HIGH_RISK_WRITE,
        reversible=True,
        rollback_tool="reverse_refund",
        estimated_value=support_service.get_order("ORD-1002").total,
    )
    context = policy_engine.build_context(action, customer_id="CUS-1002")
    policy_result = policy_engine.evaluate(action, context)
    approval = approval_service.create_request(
        request_id=request_id,
        action=action,
        reason=policy_result.reason,
        policy_decision=policy_result,
    )
    print(f"Policy Decision: {policy_result.decision.value}")
    print(f"Approval ID: {approval.approval_id}")
    print(f"Order refund total before: {support_service.get_order('ORD-1002').refund_total}")
    if not approve_demo:
        print("Pending approval created. Re-run with --approve-demo to execute in this process.")
        return 0
    approval_service.approve(approval.approval_id, "demo-manager", "Approved demo refund.")
    result = action_service.execute(request_id, action, policy_result, approval.approval_id)
    print(f"Execution success: {result.success}")
    print(f"Order refund total after: {support_service.get_order('ORD-1002').refund_total}")
    try:
        action_service.execute(request_id, action, policy_result, approval.approval_id)
    except Exception as exc:
        print(f"Replay blocked: {exc}")
    print("Audit Events:")
    for event in audit_service.list_for_request(request_id):
        print(f"{event.event_type.value}\t{event.actor}\t{event.tool_name or ''}\t{event.success}")
    return 0


def run_evaluation_command(
    benchmark_path: str,
    mode: str,
    model: str | None,
    output: str,
    save_path: str | None,
    case_id: str | None,
) -> int:
    report = EvaluationService(get_settings()).run(
        benchmark_path,
        mode=EvaluationMode(mode),
        model=model,
        case_id=case_id,
    )
    if save_path:
        report.to_json_file(save_path)
    if output == "json":
        print(report.model_dump_json(indent=2))
    else:
        print(format_report(report))
    return 0 if report.failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="SupportOps Agent CLI")
    parser.add_argument("--llm-test", action="store_true", help="Run a safe LLM smoke prompt")
    parser.add_argument("--model", help="Override the configured LLM model")
    parser.add_argument("--agent", help="Run the Phase 3 tool-using agent loop")
    parser.add_argument("--customer-id", help="Synthetic customer id for --agent")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--show-trace", action="store_true", help="Show safe execution trace")
    parser.add_argument("--pending-approvals", action="store_true")
    parser.add_argument("--approve", help="Approve an in-memory approval id")
    parser.add_argument("--deny", help="Deny an in-memory approval id")
    parser.add_argument("--actor", default="demo-manager")
    parser.add_argument("--comment")
    parser.add_argument("--audit-request", help="Show in-memory audit events for a request id")
    parser.add_argument("--demo-approval-flow", action="store_true")
    parser.add_argument("--approve-demo", action="store_true")
    parser.add_argument("--evaluate", help="Run an agent evaluation benchmark JSON file")
    parser.add_argument(
        "--evaluation-mode",
        choices=[item.value for item in EvaluationMode],
        default=EvaluationMode.SCRIPTED.value,
    )
    parser.add_argument("--save", help="Save evaluation report JSON")
    parser.add_argument("--case", help="Run a single benchmark case id")
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

    if args.pending_approvals:
        return print_pending_approvals()
    if args.approve:
        return resolve_approval_command(args.approve, True, args.actor, args.comment)
    if args.deny:
        return resolve_approval_command(args.deny, False, args.actor, args.comment)
    if args.audit_request:
        service = build_agent_service()
        events = (
            service.audit_service.list_for_request(UUID(args.audit_request))
            if service.audit_service
            else []
        )
        for event in events:
            print(f"{event.timestamp.isoformat()}\t{event.event_type.value}\t{event.actor}")
        return 0
    if args.demo_approval_flow:
        return demo_approval_flow(args.approve_demo)
    if args.evaluate:
        return run_evaluation_command(
            args.evaluate,
            args.evaluation_mode,
            args.model,
            args.output,
            args.save,
            args.case,
        )
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
