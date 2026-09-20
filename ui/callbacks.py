from typing import Any

from ui.api_client import SupportOpsAPIClient
from ui.components import DEMO_DESCRIPTIONS
from ui.formatters import (
    approvals_table,
    audit_table,
    customers_table,
    decision_trace_table,
    evaluation_summary,
    failed_cases_table,
    format_agent_result,
    format_authorization_panel,
    format_customer,
    format_error,
    format_health,
    format_order,
    format_policy,
    format_ticket,
    tool_calls_table,
    tool_results_table,
)


def load_customers(client: SupportOpsAPIClient) -> tuple[str, list[list[Any]]]:
    try:
        customers = client.list_customers()
        return "Customers loaded.", customers_table(customers)
    except Exception as exc:
        return format_error(exc), []


def load_customer(client: SupportOpsAPIClient, customer_id: str) -> str:
    try:
        return format_customer(client.get_customer(customer_id.strip()))
    except Exception as exc:
        return format_error(exc)


def load_order(client: SupportOpsAPIClient, order_id: str) -> str:
    try:
        return format_order(client.get_order(order_id.strip()))
    except Exception as exc:
        return format_error(exc)


def load_ticket(client: SupportOpsAPIClient, ticket_id: str) -> str:
    try:
        return format_ticket(client.get_ticket(ticket_id.strip()))
    except Exception as exc:
        return format_error(exc)


def load_policy(client: SupportOpsAPIClient) -> str:
    try:
        return format_policy(client.get_refund_policy())
    except Exception as exc:
        return format_error(exc)


def run_live_agent(
    client: SupportOpsAPIClient,
    user_input: str,
    customer_id: str,
    model: str,
) -> tuple[str, str, list[list[Any]], list[list[Any]], list[list[Any]], list[list[Any]], str]:
    try:
        result = client.submit_agent_request(
            user_input.strip(),
            customer_id.strip() or None,
            model or None,
        )
        return _agent_outputs(result)
    except Exception as exc:
        return format_error(exc), "", [], [], [], [], ""


def run_scripted_demo(
    client: SupportOpsAPIClient,
    scenario_id: str,
) -> tuple[str, str, list[list[Any]], list[list[Any]], list[list[Any]], list[list[Any]], str]:
    try:
        result = client.run_demo_scenario(scenario_id)
        summary = f"Deterministic demo - no live LLM used.\n{DEMO_DESCRIPTIONS[scenario_id]}\n\n"
        status, auth, calls, results, approvals, trace, request_id = _agent_outputs(result)
        return summary + status, auth, calls, results, approvals, trace, request_id
    except Exception as exc:
        return format_error(exc), "", [], [], [], [], ""


def _agent_outputs(result: dict[str, Any]):
    return (
        format_agent_result(result),
        format_authorization_panel(result),
        tool_calls_table(result),
        tool_results_table(result),
        approvals_table(result.get("approvals_required", [])),
        decision_trace_table(result),
        result.get("request_id", ""),
    )


def refresh_approvals(client: SupportOpsAPIClient) -> tuple[str, list[list[Any]]]:
    try:
        approvals = client.list_pending_approvals()
        return f"{len(approvals)} pending approval(s).", approvals_table(approvals)
    except Exception as exc:
        return format_error(exc), []


def approve_selected(
    client: SupportOpsAPIClient,
    approval_id: str,
    actor: str,
    comment: str,
) -> tuple[str, list[list[Any]]]:
    if not actor.strip():
        return "Actor is required.", []
    try:
        result = client.approve(approval_id.strip(), actor.strip(), comment.strip() or None)
        approvals = client.list_pending_approvals()
        return format_agent_result(result), approvals_table(approvals)
    except Exception as exc:
        return format_error(exc), []


def deny_selected(
    client: SupportOpsAPIClient,
    approval_id: str,
    actor: str,
    comment: str,
) -> tuple[str, list[list[Any]]]:
    if not actor.strip():
        return "Actor is required.", []
    try:
        result = client.deny(approval_id.strip(), actor.strip(), comment.strip() or None)
        approvals = client.list_pending_approvals()
        return format_agent_result(result), approvals_table(approvals)
    except Exception as exc:
        return format_error(exc), []


def load_audit(client: SupportOpsAPIClient, request_id: str) -> tuple[str, list[list[Any]]]:
    try:
        events = client.get_request_audit(request_id.strip())
        return f"{len(events)} audit event(s).", audit_table(events)
    except Exception as exc:
        return format_error(exc), []


def recent_audit(client: SupportOpsAPIClient, limit: int) -> tuple[str, list[list[Any]]]:
    try:
        events = client.get_recent_audit(int(limit))
        return f"{len(events)} recent audit event(s).", audit_table(events)
    except Exception as exc:
        return format_error(exc), []


def run_evaluation(
    client: SupportOpsAPIClient,
    benchmark: str,
    mode: str,
    model: str,
    case_id: str,
) -> tuple[str, list[list[Any]]]:
    try:
        result = client.run_evaluation(
            benchmark=benchmark,
            mode=mode,
            model=model if mode == "live" else None,
            case_id=case_id.strip() or None,
        )
        return evaluation_summary(result), failed_cases_table(result)
    except Exception as exc:
        return format_error(exc), []


def refresh_system(client: SupportOpsAPIClient) -> str:
    try:
        return format_health(client.health(), client.ollama_health(), client.state_health())
    except Exception as exc:
        return format_error(exc)


def reset_demo(client: SupportOpsAPIClient, confirm: bool) -> str:
    if not confirm:
        return "Check the confirmation box before resetting synthetic demo state."
    try:
        client.reset_demo(confirm=True)
        return "Synthetic demo state reset."
    except Exception as exc:
        return format_error(exc)


def load_benchmarks(client: SupportOpsAPIClient) -> list[str]:
    try:
        return [item["benchmark_id"] for item in client.list_benchmarks()]
    except Exception:
        return ["support-agent-demo"]
