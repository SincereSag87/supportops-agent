import httpx
import pytest

from ui.api_client import SupportOpsAPIClient
from ui.models import UIClientError


def make_client(handler) -> SupportOpsAPIClient:
    return SupportOpsAPIClient(
        base_url="http://testserver",
        timeout=1,
        transport=httpx.MockTransport(handler),
    )


def json_response(status: int, payload: dict | list) -> httpx.Response:
    return httpx.Response(status, json=payload)


def test_api_client_health_support_agent_approvals_audit_evaluation_demo_reset() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        routes = {
            "/health": {"status": "ok"},
            "/health/ollama": {"reachable": False},
            "/health/state": {"customers": 5},
            "/metrics": {"requests": {"requests_total": 1}},
            "/customers": [{"customer_id": "CUS-1001"}],
            "/customers/CUS-1001": {"customer_id": "CUS-1001"},
            "/orders/ORD-1001": {"order_id": "ORD-1001"},
            "/customers/CUS-1001/orders": [{"order_id": "ORD-1001"}],
            "/tickets/TIC-1001": {"ticket_id": "TIC-1001"},
            "/customers/CUS-1001/tickets": [{"ticket_id": "TIC-1001"}],
            "/policies/refund": {"return_window_days": 30},
            "/approvals/pending": [{"approval_id": "APP-1"}],
            "/approvals/APP-1": {"approval_id": "APP-1"},
            "/audit/requests/REQ-1": [{"event_type": "request_received"}],
            "/audit/recent": [{"event_type": "request_received"}],
            "/evaluation/benchmarks": [{"benchmark_id": "support-agent-demo"}],
        }
        if request.url.path in routes:
            return json_response(200, routes[request.url.path])
        if request.url.path in {
            "/agent/requests",
            "/approvals/APP-1/approve",
            "/approvals/APP-1/deny",
            "/evaluation/run",
            "/demo/scenarios/order-status",
            "/demo/reset",
        }:
            return json_response(200, {"status": "completed"})
        return json_response(404, {"error": {"code": "NOT_FOUND", "message": "missing"}})

    client = make_client(handler)

    assert client.health()["status"] == "ok"
    assert client.ollama_health()["reachable"] is False
    assert client.state_health()["customers"] == 5
    assert client.metrics()["requests"]["requests_total"] == 1
    assert client.list_customers()[0]["customer_id"] == "CUS-1001"
    assert client.get_customer("CUS-1001")["customer_id"] == "CUS-1001"
    assert client.get_order("ORD-1001")["order_id"] == "ORD-1001"
    assert client.get_customer_orders("CUS-1001")[0]["order_id"] == "ORD-1001"
    assert client.get_ticket("TIC-1001")["ticket_id"] == "TIC-1001"
    assert client.get_customer_tickets("CUS-1001")[0]["ticket_id"] == "TIC-1001"
    assert client.get_refund_policy()["return_window_days"] == 30
    assert client.submit_agent_request("hello")["status"] == "completed"
    assert client.list_pending_approvals()[0]["approval_id"] == "APP-1"
    assert client.get_approval("APP-1")["approval_id"] == "APP-1"
    assert client.approve("APP-1", "demo-manager")["status"] == "completed"
    assert client.deny("APP-1", "demo-manager")["status"] == "completed"
    assert client.get_request_audit("REQ-1")[0]["event_type"] == "request_received"
    assert client.get_recent_audit()[0]["event_type"] == "request_received"
    assert client.list_benchmarks()[0]["benchmark_id"] == "support-agent-demo"
    assert client.run_evaluation("support-agent-demo")["status"] == "completed"
    assert client.run_demo_scenario("order-status")["status"] == "completed"
    assert client.reset_demo()["status"] == "completed"
    assert ("POST", "/agent/requests") in seen


def test_api_client_friendly_errors_and_malformed_response() -> None:
    model_client = make_client(
        lambda request: json_response(
            503,
            {
                "error": {
                    "code": "MODEL_NOT_AVAILABLE",
                    "message": "model missing",
                }
            },
        )
    )
    consumed_client = make_client(
        lambda request: json_response(
            409,
            {
                "error": {
                    "code": "APPROVALCONSUMEDERROR",
                    "message": "consumed",
                }
            },
        )
    )
    malformed_client = SupportOpsAPIClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="not json")),
    )

    with pytest.raises(UIClientError, match="selected local model"):
        model_client.health()
    with pytest.raises(UIClientError, match="already been used"):
        consumed_client.health()
    with pytest.raises(UIClientError, match="malformed"):
        malformed_client.health()


def test_api_client_backend_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(UIClientError, match="unavailable"):
        make_client(handler).health()
