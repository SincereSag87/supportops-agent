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
    format_health,
    format_order,
    format_policy,
    format_ticket,
    tool_calls_table,
    tool_results_table,
)


def test_format_business_objects_and_system_health() -> None:
    assert "Jordan" in format_customer(
        {
            "customer_id": "CUS-1001",
            "name": "Jordan Lee",
            "email": "jordan.lee@example.test",
            "status": "active",
            "order_ids": ["ORD-1001"],
            "open_ticket_ids": ["TIC-1001"],
        }
    )
    assert "79.99" in format_order(
        {
            "order_id": "ORD-1001",
            "customer_id": "CUS-1001",
            "items": [
                {
                    "quantity": 1,
                    "product_name": "Wireless Headphones",
                    "unit_price": "74.99",
                }
            ],
            "total": "79.99",
            "currency": "USD",
            "status": "delivered",
            "delivered_at": "2026-09-12T00:00:00Z",
            "refund_total": "0.00",
            "remaining_refundable_amount": "79.99",
        }
    )
    assert "Damaged" in format_ticket(
        {
            "ticket_id": "TIC-1001",
            "customer_id": "CUS-1001",
            "order_id": "ORD-1001",
            "subject": "Damaged headphones",
            "status": "open",
            "priority": "normal",
            "description": "Damaged",
        }
    )
    assert "language model cannot change" in format_policy(
        {
            "policy_version": "v1",
            "return_window_days": 30,
            "auto_refund_limit": "100.00",
            "approval_refund_limit": "500.00",
            "requires_delivered_order": True,
            "allowed_reasons": ["damaged"],
        }
    )
    assert "Customers: 5" in format_health(
        {"status": "ok", "service": "supportops-agent"},
        {"reachable": False, "default_model": "llama3.2"},
        {
            "customers": 5,
            "orders": 9,
            "tickets": 5,
            "refunds": 0,
            "pending_approvals": 0,
            "audit_events": 0,
        },
    )


def test_format_tables_agent_result_and_evaluation() -> None:
    result = {
        "status": "awaiting_approval",
        "escalated": False,
        "request_id": "REQ-1",
        "response": "Approval required.",
        "tool_calls": [
            {
                "tool_name": "issue_refund",
                "arguments": {"amount": "299.99"},
                "call_id": "CALL-1",
            }
        ],
        "tool_results": [
            {
                "tool_name": "issue_refund",
                "success": True,
                "error": None,
                "reversible": True,
                "metadata": {},
            }
        ],
        "approvals_required": [
            {"policy_decision": "require_approval", "approval_id": "APP-1"}
        ],
        "decision_trace": [
            {
                "decision_type": "tool_call",
                "reasoning_summary": "Needs approval.",
                "tool_name": "issue_refund",
            }
        ],
    }
    report = {
        "cases": 19,
        "passed": 19,
        "failed": 0,
        "task_success_rate": 1.0,
        "tool_selection_accuracy": 1.0,
        "policy_accuracy": 1.0,
        "approval_accuracy": 1.0,
        "action_safety_accuracy": 1.0,
        "final_state_accuracy": 1.0,
        "audit_completeness": 1.0,
        "failure_recovery_rate": 1.0,
        "parse_success_rate": 0.95,
        "average_steps": 2,
        "average_latency_ms": 3,
        "failed_cases": [{"case_id": "bad", "failed_checks": ["status"]}],
    }
    customer_rows = customers_table(
        [{"customer_id": "CUS-1001", "name": "Jordan", "email": "x", "status": "active"}]
    )

    assert customer_rows
    assert approvals_table([{"approval_id": "APP-1"}])[0][0] == "APP-1"
    assert audit_table([{"event_type": "request_received"}])[0][1] == "request_received"
    assert tool_calls_table(result)[0][0] == "issue_refund"
    assert tool_results_table(result)[0][1] is True
    assert decision_trace_table(result)[0][1] == "tool_call"
    assert "Approval required" in format_agent_result(result)
    assert "Approval required: Yes" in format_authorization_panel(result)
    assert "Cases: 19" in evaluation_summary(report)
    assert failed_cases_table(report)[0][0] == "bad"
