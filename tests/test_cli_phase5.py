import sys
from pathlib import Path

from app.main import main


def test_cli_evaluate_text(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["app.main", "--evaluate", "benchmarks/support_agent_eval.json", "--case", "order-status"],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert "Benchmark:" in output
    assert "Passed: 1" in output


def test_cli_evaluate_json_and_save(capsys, monkeypatch, tmp_path: Path) -> None:
    save_path = tmp_path / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.main",
            "--evaluate",
            "benchmarks/support_agent_eval.json",
            "--case",
            "low-value-refund",
            "--output",
            "json",
            "--save",
            str(save_path),
        ],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert '"case_count": 1' in output
    assert save_path.exists()
