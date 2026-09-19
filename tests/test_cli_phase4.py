import sys

from app.main import main


def test_cli_pending_approvals_header(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["app.main", "--pending-approvals"])

    assert main() == 0
    assert "Approval ID" in capsys.readouterr().out


def test_cli_demo_approval_flow_pending(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["app.main", "--demo-approval-flow"])

    assert main() == 0
    output = capsys.readouterr().out
    assert "Policy Decision: require_approval" in output
    assert "Pending approval created" in output


def test_cli_demo_approval_flow_approved_and_replay_blocked(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["app.main", "--demo-approval-flow", "--approve-demo"])

    assert main() == 0
    output = capsys.readouterr().out
    assert "Execution success: True" in output
    assert "Order refund total after: 299.99" in output
    assert "Replay blocked:" in output
    assert "approval_consumed" in output
