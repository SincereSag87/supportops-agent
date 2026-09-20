from ui import components
from ui.api_client import SupportOpsAPIClient
from ui.app import build_app


def test_component_constants() -> None:
    assert "order-status" in components.DEMO_SCENARIOS
    assert components.APPROVAL_COLUMNS[0] == "Approval ID"
    assert components.TRACE_COLUMNS[2] == "Safe rationale"


def test_build_app_returns_blocks() -> None:
    app = build_app(SupportOpsAPIClient(base_url="http://127.0.0.1:8000"))
    assert app.title == "SupportOps Agent"
