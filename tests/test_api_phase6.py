from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.dependencies import get_container


def client() -> TestClient:
    get_container.cache_clear()
    return TestClient(create_app())


def test_health_openapi_and_state_endpoints() -> None:
    api = client()

    assert api.get("/health").json() == {"status": "ok", "service": "supportops-agent"}
    assert api.get("/health/ollama").status_code == 200
    state = api.get("/health/state").json()
    assert state["customers"] == 5
    assert state["orders"] >= 8
    assert state["pending_approvals"] == 0
    assert api.get("/docs").status_code == 200
    openapi = api.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    assert "/agent/requests" in paths
    assert "/approvals/pending" in paths
    assert "/evaluation/run" in paths
    assert "/metrics" in paths


def test_request_id_and_metrics_endpoint() -> None:
    api = client()

    response = api.get("/health", headers={"X-Request-ID": "demo-request-1"})

    assert response.headers["X-Request-ID"] == "demo-request-1"
    metrics = api.get("/metrics").json()
    assert metrics["requests"]["requests_total"] >= 1
    assert metrics["requests"]["requests_successful"] >= 1
    assert "average_request_latency_ms" in metrics["requests"]


def test_support_read_endpoints_and_missing_records() -> None:
    api = client()

    customers = api.get("/customers")
    assert customers.status_code == 200
    assert customers.json()[0]["email"].endswith("@example.test")
    assert api.get("/customers/CUS-1001").json()["order_ids"]
    order = api.get("/orders/ORD-1001").json()
    assert order["status"] == "delivered"
    assert order["remaining_refundable_amount"] == "79.99"
    assert api.get("/customers/CUS-1001/orders").status_code == 200
    assert api.get("/tickets/TIC-1001").status_code == 200
    assert api.get("/customers/CUS-1001/tickets").status_code == 200
    assert api.get("/policies/refund").json()["return_window_days"] == 30
    assert api.get("/orders/ORD-9999").status_code == 404


def test_agent_live_model_unavailable_returns_structured_error() -> None:
    api = client()

    response = api.post(
        "/agent/requests",
        json={"user_input": "What is order ORD-1001?", "customer_id": "CUS-1001"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] in {"LLM_UNAVAILABLE", "MODEL_NOT_AVAILABLE"}


def test_demo_order_low_high_ticket_and_reset() -> None:
    api = client()

    assert api.post("/demo/reset", json={"confirm": False}).status_code == 400
    assert api.post("/demo/reset", json={"confirm": True}).json()["status"] == "reset"

    order_status = api.post("/demo/scenarios/order-status")
    assert order_status.status_code == 200
    assert "delivered" in order_status.json()["response"].lower()

    low = api.post("/demo/scenarios/low-refund")
    assert low.status_code == 200
    assert low.json()["status"] == "completed"
    assert api.get("/orders/ORD-1001").json()["refund_total"] == "79.99"

    api.post("/demo/reset", json={"confirm": True})
    high = api.post("/demo/scenarios/high-refund")
    assert high.json()["status"] == "escalated"
    assert api.get("/orders/ORD-1003").json()["refund_total"] == "0.00"

    ticket_count = api.get("/health/state").json()["tickets"]
    ticket = api.post("/demo/scenarios/ticket-create")
    assert ticket.json()["status"] == "completed"
    assert api.get("/health/state").json()["tickets"] == ticket_count + 1


def test_end_to_end_medium_refund_approval_replay_and_audit() -> None:
    api = client()
    api.post("/demo/reset", json={"confirm": True})

    pending = api.post("/demo/scenarios/medium-refund")
    body = pending.json()
    approval_id = body["approvals_required"][0]["approval_id"]
    request_id = body["request_id"]

    assert body["status"] == "awaiting_approval"
    assert api.get("/orders/ORD-1002").json()["refund_total"] == "0.00"
    assert any(
        approval["approval_id"] == approval_id
        for approval in api.get("/approvals/pending").json()
    )
    approval_detail = api.get(f"/approvals/{approval_id}")
    assert approval_detail.status_code == 200
    assert approval_detail.json()["status"] == "pending"

    approved = api.post(
        f"/approvals/{approval_id}/approve",
        json={"actor": "demo-manager", "comment": "Approved for demo."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert api.get("/orders/ORD-1002").json()["refund_total"] == "299.99"

    replay = api.post(
        f"/approvals/{approval_id}/approve",
        json={"actor": "demo-manager", "comment": "Again."},
    )
    assert replay.status_code == 409
    metrics = api.get("/metrics").json()
    assert metrics["approvals"]["approval_replay_blocks"] >= 1
    assert metrics["safety"]["unauthorized_action_blocks"] >= 1

    audit = api.get(f"/audit/requests/{request_id}").json()
    event_types = [event["event_type"] for event in audit]
    assert event_types.index("approval_requested") < event_types.index("approval_granted")
    assert "action_executed" in event_types
    assert "approval_consumed" in event_types


def test_approval_denial_and_missing_approval() -> None:
    api = client()
    pending = api.post("/demo/scenarios/medium-refund").json()
    approval_id = pending["approvals_required"][0]["approval_id"]

    denied = api.post(
        f"/approvals/{approval_id}/deny",
        json={"actor": "demo-manager", "comment": "Denied."},
    )
    assert denied.status_code == 200
    assert api.get("/orders/ORD-1002").json()["refund_total"] == "0.00"
    assert api.post(
        f"/approvals/{approval_id}/approve",
        json={"actor": "demo-manager"},
    ).status_code == 409
    assert api.get("/approvals/00000000-0000-4000-8000-000000000099").status_code == 404


def test_evaluation_endpoints() -> None:
    api = client()

    benchmarks = api.get("/evaluation/benchmarks")
    assert benchmarks.status_code == 200
    assert benchmarks.json()[0]["benchmark_id"] == "support-agent-demo"

    report = api.post(
        "/evaluation/run",
        json={"benchmark": "support-agent-demo", "mode": "scripted", "case_id": "order-status"},
    )
    assert report.status_code == 200
    assert report.json()["passed"] == 1

    full = api.post("/evaluation/run", json={"benchmark": "support-agent-demo"})
    assert full.status_code == 200
    assert full.json()["cases"] == 19
    assert full.json()["failed"] == 0

    assert api.post("/evaluation/run", json={"benchmark": "missing"}).status_code == 404
