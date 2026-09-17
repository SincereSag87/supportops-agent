import sys
from uuid import uuid4

from app.agent.decisions import AgentDecision, AgentDecisionType
from app.agent.models import AgentStatus
from app.agent.results import AgentResult


class FakeAgentService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def handle_request(self, user_input: str, customer_id=None, model=None) -> AgentResult:
        self.calls.append({"user_input": user_input, "customer_id": customer_id, "model": model})
        return AgentResult(
            request_id=uuid4(),
            status=AgentStatus.COMPLETED,
            response="ORD-1001 was delivered.",
            decision_history=[
                AgentDecision(
                    decision_type=AgentDecisionType.FINAL_RESPONSE,
                    reasoning_summary="Order data is available.",
                    final_response="ORD-1001 was delivered.",
                )
            ],
        )


def test_cli_agent_text_with_customer_model_and_trace(capsys, monkeypatch) -> None:
    from app import main as main_module

    fake = FakeAgentService()
    monkeypatch.setattr(main_module, "build_agent_service", lambda: fake)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.main",
            "--agent",
            "What is the status of ORD-1001?",
            "--customer-id",
            "CUS-1001",
            "--model",
            "gemma3",
            "--show-trace",
        ],
    )

    assert main_module.main() == 0
    output = capsys.readouterr().out
    assert "Status: completed" in output
    assert "Execution Trace:" in output
    assert "chain-of-thought" not in output.lower()
    assert fake.calls[0]["customer_id"] == "CUS-1001"
    assert fake.calls[0]["model"] == "gemma3"


def test_cli_agent_json_output(capsys, monkeypatch) -> None:
    from app import main as main_module

    monkeypatch.setattr(main_module, "build_agent_service", lambda: FakeAgentService())
    monkeypatch.setattr(
        sys,
        "argv",
        ["app.main", "--agent", "Status?", "--customer-id", "CUS-1001", "--output", "json"],
    )

    assert main_module.main() == 0
    output = capsys.readouterr().out
    assert '"status": "completed"' in output
    assert '"response": "ORD-1001 was delivered."' in output
