import sys

from app.main import main


def test_cli_list_tools(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["app.main", "--list-tools"])

    assert main() == 0
    output = capsys.readouterr().out
    assert "customer_lookup" in output
    assert "issue_refund" in output


def test_cli_read_customer_and_order_commands(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["app.main", "--customer", "CUS-1001"])
    assert main() == 0
    customer_output = capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["app.main", "--order", "ORD-1001"])
    assert main() == 0
    order_output = capsys.readouterr().out

    assert "Jordan Lee" in customer_output
    assert "Wireless Headphones" in order_output
    assert "79.99" in order_output
    assert "delivered" in order_output


def test_cli_policy_command(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["app.main", "--refund-policy"])

    assert main() == 0
    output = capsys.readouterr().out
    assert "Return window: 30 days" in output
    assert "Automatic refund threshold: 100.00" in output
    assert "Approval threshold: 500.00" in output


def test_cli_write_tool_requires_confirmation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.main",
            "--tool",
            "issue_refund",
            "--input",
            '{"order_id":"ORD-1001","amount":"10.00","reason":"damaged","idempotency_key":"cli"}',
        ],
    )

    assert main() == 1
    output = capsys.readouterr().out
    assert "Refusing to execute write tool without --confirm-write." in output


def test_cli_write_tool_with_confirmation_executes(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.main",
            "--tool",
            "issue_refund",
            "--input",
            '{"order_id":"ORD-1001","amount":"10.00","reason":"damaged","idempotency_key":"cli"}',
            "--confirm-write",
        ],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert '"success": true' in output
    assert '"order_refund_total": "10.00"' in output


def test_cli_write_tool_with_input_file_executes(capsys, monkeypatch, tmp_path) -> None:
    payload = tmp_path / "refund.json"
    payload.write_text(
        '{"order_id":"ORD-1001","amount":"10.00","reason":"damaged","idempotency_key":"file-cli"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.main",
            "--tool",
            "issue_refund",
            "--input-file",
            str(payload),
            "--confirm-write",
        ],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert '"success": true' in output
    assert '"order_refund_total": "10.00"' in output
