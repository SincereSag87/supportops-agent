from typing import Any


def status_message(label: str, payload: Any) -> str:
    return f"{label} loaded." if payload else f"{label} unavailable."


def format_error(exc: Exception) -> str:
    return str(exc)


def format_health(health: dict, ollama: dict, state: dict) -> str:
    return "\n".join(
        [
            f"API: {health.get('status', 'unknown')}",
            f"Service: {health.get('service', 'supportops-agent')}",
            f"Ollama reachable: {ollama.get('reachable')}",
            f"Default model: {ollama.get('default_model')}",
            f"Customers: {state.get('customers')}",
            f"Orders: {state.get('orders')}",
            f"Tickets: {state.get('tickets')}",
            f"Refunds: {state.get('refunds')}",
            f"Pending approvals: {state.get('pending_approvals')}",
            f"Audit events: {state.get('audit_events')}",
        ]
    )


def format_customer(customer: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Customer ID: {customer.get('customer_id')}",
            f"Name: {customer.get('name')}",
            f"Email: {customer.get('email')}",
            f"Status: {customer.get('status')}",
            f"Orders: {', '.join(customer.get('order_ids', []))}",
            f"Open tickets: {', '.join(customer.get('open_ticket_ids', []))}",
        ]
    )


def format_order(order: dict[str, Any]) -> str:
    items = order.get("items", [])
    item_lines = [
        f"- {item.get('quantity')} x {item.get('product_name')} @ {item.get('unit_price')}"
        for item in items
    ]
    return "\n".join(
        [
            f"Order ID: {order.get('order_id')}",
            f"Customer: {order.get('customer_id')}",
            "Items:",
            *item_lines,
            f"Total: {order.get('total')} {order.get('currency')}",
            f"Status: {order.get('status')}",
            f"Delivered: {order.get('delivered_at') or 'not delivered'}",
            f"Refund total: {order.get('refund_total')} {order.get('currency')}",
            (
                "Remaining refundable: "
                f"{order.get('remaining_refundable_amount')} {order.get('currency')}"
            ),
        ]
    )


def format_ticket(ticket: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Ticket ID: {ticket.get('ticket_id')}",
            f"Customer: {ticket.get('customer_id')}",
            f"Order: {ticket.get('order_id')}",
            f"Subject: {ticket.get('subject')}",
            f"Status: {ticket.get('status')}",
            f"Priority: {ticket.get('priority')}",
            f"Description: {ticket.get('description')}",
            f"Resolution: {ticket.get('resolution') or 'none'}",
        ]
    )


def format_policy(policy: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Policy version: {policy.get('policy_version')}",
            f"Return window: {policy.get('return_window_days')} days",
            f"Auto-refund threshold: {policy.get('auto_refund_limit')}",
            f"Approval threshold: {policy.get('approval_refund_limit')}",
            f"Requires delivered order: {policy.get('requires_delivered_order')}",
            f"Allowed reasons: {', '.join(policy.get('allowed_reasons', []))}",
            "",
            "The policy shown here is application data. "
            "The language model cannot change these thresholds.",
        ]
    )


def customers_table(customers: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [item.get("customer_id"), item.get("name"), item.get("email"), item.get("status")]
        for item in customers
    ]


def approvals_table(approvals: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            item.get("approval_id"),
            item.get("request_id"),
            item.get("tool_name"),
            item.get("action_type"),
            item.get("amount"),
            item.get("policy_reason"),
            item.get("status"),
            item.get("requested_at"),
        ]
        for item in approvals
    ]


def audit_table(events: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            item.get("timestamp"),
            item.get("event_type"),
            item.get("actor"),
            item.get("tool_name"),
            item.get("success"),
            item.get("details"),
        ]
        for item in events
    ]


def tool_calls_table(result: dict[str, Any]) -> list[list[Any]]:
    return [
        [call.get("tool_name"), call.get("arguments"), call.get("call_id")]
        for call in result.get("tool_calls", [])
    ]


def tool_results_table(result: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            item.get("tool_name"),
            item.get("success"),
            item.get("error"),
            item.get("reversible"),
            item.get("metadata"),
        ]
        for item in result.get("tool_results", [])
    ]


def decision_trace_table(result: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            index,
            item.get("decision_type"),
            item.get("reasoning_summary"),
            item.get("tool_name"),
        ]
        for index, item in enumerate(result.get("decision_trace", []), start=1)
    ]


def format_agent_result(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Status: {result.get('status')}",
            f"Escalated: {'Yes' if result.get('escalated') else 'No'}",
            f"Request ID: {result.get('request_id')}",
            "",
            result.get("response") or "",
        ]
    )


def format_authorization_panel(result: dict[str, Any]) -> str:
    approvals = result.get("approvals_required", [])
    executed = any(item.get("success") for item in result.get("tool_results", []))
    policy = None
    if approvals:
        policy = approvals[0].get("policy_decision")
    return "\n".join(
        [
            f"Policy decision: {policy or 'not returned'}",
            f"Approval required: {'Yes' if approvals else 'No'}",
            f"Action executed: {'Yes' if executed else 'No'}",
            "Authorization is decided by application services, not by model text.",
        ]
    )


def evaluation_summary(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Cases: {report.get('cases')}",
            f"Passed: {report.get('passed')}",
            f"Failed: {report.get('failed')}",
            f"Task success rate: {report.get('task_success_rate')}",
            f"Tool selection accuracy: {report.get('tool_selection_accuracy')}",
            f"Policy accuracy: {report.get('policy_accuracy')}",
            f"Approval accuracy: {report.get('approval_accuracy')}",
            f"Action safety accuracy: {report.get('action_safety_accuracy')}",
            f"Final-state accuracy: {report.get('final_state_accuracy')}",
            f"Audit completeness: {report.get('audit_completeness')}",
            f"Failure recovery: {report.get('failure_recovery_rate')}",
            f"Parse success: {report.get('parse_success_rate')}",
            f"Average steps: {report.get('average_steps')}",
            f"Average latency ms: {report.get('average_latency_ms')}",
        ]
    )


def failed_cases_table(report: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            item.get("case_id"),
            item.get("expected_status"),
            item.get("actual_status"),
            ", ".join(item.get("failed_checks", [])),
            item.get("actual_tools"),
            item.get("actual_policy_decision"),
            item.get("approval_status"),
            {
                "refund_total": item.get("refund_total"),
                "ticket_delta": item.get("ticket_count_delta"),
            },
            item.get("error"),
        ]
        for item in report.get("failed_cases", [])
    ]
