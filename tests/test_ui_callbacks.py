from ui import callbacks


class FakeClient:
    def list_customers(self):
        return [
            {
                "customer_id": "CUS-1001",
                "name": "Jordan",
                "email": "jordan.lee@example.test",
                "status": "active",
            }
        ]

    def get_customer(self, customer_id):
        return {
            "customer_id": customer_id,
            "name": "Jordan",
            "email": "jordan.lee@example.test",
            "status": "active",
            "order_ids": ["ORD-1001"],
            "open_ticket_ids": [],
        }

    def get_order(self, order_id):
        return {
            "order_id": order_id,
            "customer_id": "CUS-1001",
            "items": [],
            "total": "79.99",
            "currency": "USD",
            "status": "delivered",
            "refund_total": "0.00",
            "remaining_refundable_amount": "79.99",
        }

    def get_ticket(self, ticket_id):
        return {
            "ticket_id": ticket_id,
            "customer_id": "CUS-1001",
            "order_id": "ORD-1001",
            "subject": "Damaged",
            "status": "open",
            "priority": "normal",
            "description": "Damaged",
        }

    def get_refund_policy(self):
        return {
            "policy_version": "v1",
            "return_window_days": 30,
            "auto_refund_limit": "100.00",
            "approval_refund_limit": "500.00",
            "requires_delivered_order": True,
            "allowed_reasons": ["damaged"],
        }

    def submit_agent_request(self, *args, **kwargs):
        return agent_result()

    def run_demo_scenario(self, scenario_id):
        return agent_result()

    def list_pending_approvals(self):
        return [
            {
                "approval_id": "APP-1",
                "request_id": "REQ-1",
                "tool_name": "issue_refund",
                "action_type": "issue_refund",
                "amount": "299.99",
                "policy_reason": "approval",
                "status": "pending",
                "requested_at": "now",
            }
        ]

    def approve(self, *args, **kwargs):
        return agent_result(status="completed", response="Approved action executed.")

    def deny(self, *args, **kwargs):
        return agent_result(status="completed", response="Approval denied.")

    def get_request_audit(self, request_id):
        return [{"timestamp": "now", "event_type": "approval_requested"}]

    def get_recent_audit(self, limit):
        return [{"timestamp": "now", "event_type": "request_received"}]

    def run_evaluation(self, *args, **kwargs):
        return {
            "cases": 1,
            "passed": 1,
            "failed": 0,
            "task_success_rate": 1,
            "tool_selection_accuracy": 1,
            "policy_accuracy": 1,
            "approval_accuracy": 1,
            "action_safety_accuracy": 1,
            "final_state_accuracy": 1,
            "audit_completeness": 1,
            "failure_recovery_rate": 1,
            "parse_success_rate": 1,
            "average_steps": 1,
            "average_latency_ms": 1,
            "failed_cases": [],
        }

    def health(self):
        return {"status": "ok", "service": "supportops-agent"}

    def ollama_health(self):
        return {"reachable": False, "default_model": "llama3.2"}

    def state_health(self):
        return {
            "customers": 5,
            "orders": 9,
            "tickets": 5,
            "refunds": 0,
            "pending_approvals": 1,
            "audit_events": 3,
        }

    def metrics(self):
        return {
            "requests": {
                "requests_total": 1,
                "requests_successful": 1,
                "requests_failed": 0,
                "average_request_latency_ms": 2,
            },
            "agent": {"agent_requests": 1, "completed": 1},
            "policy": {},
            "approvals": {},
            "tools": {},
            "safety": {},
            "evaluation": {},
        }

    def reset_demo(self, confirm=True):
        return {"status": "reset"}

    def list_benchmarks(self):
        return [{"benchmark_id": "support-agent-demo"}]


def agent_result(status="awaiting_approval", response="Approval required."):
    return {
        "status": status,
        "response": response,
        "request_id": "REQ-1",
        "escalated": False,
        "tool_calls": [],
        "tool_results": [],
        "approvals_required": [],
        "decision_trace": [],
    }


def test_callbacks_happy_paths() -> None:
    client = FakeClient()

    assert callbacks.load_customers(client)[1][0][0] == "CUS-1001"
    assert "Jordan" in callbacks.load_customer(client, "CUS-1001")
    assert "ORD-1001" in callbacks.load_order(client, "ORD-1001")
    assert "Damaged" in callbacks.load_ticket(client, "TIC-1001")
    assert "Return window" in callbacks.load_policy(client)
    assert callbacks.run_live_agent(client, "hello", "CUS-1001", "llama3.2")[6] == "REQ-1"
    assert "Deterministic demo" in callbacks.run_scripted_demo(client, "order-status")[0]
    assert callbacks.refresh_approvals(client)[1][0][0] == "APP-1"
    assert "Approved" in callbacks.approve_selected(client, "APP-1", "demo-manager", "")[0]
    assert "denied" in callbacks.deny_selected(client, "APP-1", "demo-manager", "")[0].lower()
    assert callbacks.load_audit(client, "REQ-1")[1][0][1] == "approval_requested"
    assert callbacks.recent_audit(client, 50)[1][0][1] == "request_received"
    eval_result = callbacks.run_evaluation(client, "support-agent-demo", "scripted", "", "")
    assert "Cases: 1" in eval_result[0]
    assert "Customers: 5" in callbacks.refresh_system(client)
    assert callbacks.reset_demo(client, False).startswith("Check")
    assert callbacks.reset_demo(client, True) == "Synthetic demo state reset."
    assert callbacks.load_benchmarks(client) == ["support-agent-demo"]


def test_callbacks_validation_and_errors() -> None:
    client = FakeClient()
    assert callbacks.approve_selected(client, "APP-1", "", "")[0] == "Actor is required."
    assert callbacks.deny_selected(client, "APP-1", "", "")[0] == "Actor is required."
