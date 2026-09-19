from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.models import AgentStatus
from app.audit.models import AuditEventType
from app.evaluation.dataset import load_benchmark
from app.evaluation.metrics import build_report
from app.evaluation.models import (
    AgentEvaluationCaseResult,
    EvaluationMode,
    SupportAgentBenchmark,
)
from app.evaluation.runner import AgentEvaluationRunner
from app.policies.models import PolicyDecision

BENCHMARK_PATH = Path("benchmarks/support_agent_eval.json")


def test_benchmark_dataset_valid_and_has_required_cases() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)

    assert len(benchmark.cases) >= 18
    assert {case.id for case in benchmark.cases} >= {
        "order-status",
        "low-value-refund",
        "medium-refund-approved",
        "failure-audit-pre-write",
    }
    assert any(
        AuditEventType.ACTION_EXECUTED in case.expected_audit_events for case in benchmark.cases
    )


def test_benchmark_rejects_duplicate_case_ids_and_missing_cases() -> None:
    payload = {
        "name": "bad",
        "description": "bad",
        "cases": [
            {
                "id": "dup",
                "description": "one",
                "user_input": "x",
                "expected_status": "completed",
            },
            {
                "id": "dup",
                "description": "two",
                "user_input": "x",
                "expected_status": "completed",
            },
        ],
    }
    with pytest.raises(ValidationError):
        SupportAgentBenchmark.model_validate(payload)
    with pytest.raises(ValidationError):
        SupportAgentBenchmark.model_validate({"name": "bad", "description": "bad", "cases": []})


def test_metrics_aggregate_success_and_failures() -> None:
    results = [
        AgentEvaluationCaseResult(
            case_id="ok",
            mode=EvaluationMode.SCRIPTED,
            success=True,
            expected_status=AgentStatus.COMPLETED,
            actual_status=AgentStatus.COMPLETED,
            action_correct=True,
            audit_complete=True,
            parse_success=True,
        ),
        AgentEvaluationCaseResult(
            case_id="bad",
            mode=EvaluationMode.SCRIPTED,
            success=False,
            expected_status=AgentStatus.COMPLETED,
            actual_status=AgentStatus.FAILED,
            action_correct=False,
            audit_complete=False,
            parse_success=False,
            failed_checks=["status", "unsafe execution"],
        ),
    ]

    report = build_report("demo", EvaluationMode.SCRIPTED, None, results)

    assert report.case_count == 2
    assert report.task_success_rate == 0.5
    assert report.action_safety_accuracy == 0.5
    assert report.audit_completeness_rate == 0.5
    assert report.structured_parse_success_rate == 0.5
    assert report.failure_categories["status"] == 1


def test_scripted_benchmark_passes_and_isolates_fresh_state() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    report = AgentEvaluationRunner().run_dataset(benchmark, mode=EvaluationMode.SCRIPTED)
    low_again = AgentEvaluationRunner().run_dataset(
        benchmark,
        mode=EvaluationMode.SCRIPTED,
        case_id="low-value-refund",
    )

    assert report.failed == 0
    assert report.action_safety_accuracy == 1.0
    assert report.policy_accuracy == 1.0
    assert report.audit_completeness_rate == 1.0
    assert low_again.cases[0].refund_total == "79.99"


def test_normal_policy_and_approval_scenarios() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    runner = AgentEvaluationRunner()

    low = runner.run_dataset(benchmark, mode=EvaluationMode.SCRIPTED, case_id="low-value-refund")
    medium = runner.run_dataset(
        benchmark,
        mode=EvaluationMode.SCRIPTED,
        case_id="medium-refund-pending",
    )
    approved = runner.run_dataset(
        benchmark,
        mode=EvaluationMode.SCRIPTED,
        case_id="medium-refund-approved",
    )
    high = runner.run_dataset(benchmark, mode=EvaluationMode.SCRIPTED, case_id="high-value-refund")

    assert low.cases[0].actual_policy_decision == PolicyDecision.ALLOW
    assert low.cases[0].refund_total == "79.99"
    assert medium.cases[0].actual_status == AgentStatus.AWAITING_APPROVAL
    assert approved.cases[0].refund_total == "299.99"
    assert high.cases[0].actual_status == AgentStatus.ESCALATED


def test_failure_recovery_and_audit_fail_closed() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    runner = AgentEvaluationRunner()

    repaired = runner.run_dataset(
        benchmark,
        mode=EvaluationMode.SCRIPTED,
        case_id="failure-malformed-json-repair",
    ).cases[0]
    audit_failure = runner.run_dataset(
        benchmark,
        mode=EvaluationMode.SCRIPTED,
        case_id="failure-audit-pre-write",
    ).cases[0]
    timeout = runner.run_dataset(
        benchmark,
        mode=EvaluationMode.SCRIPTED,
        case_id="failure-llm-timeout",
    ).cases[0]

    assert repaired.success is True
    assert repaired.failure_recovered is True
    assert audit_failure.refund_total == "0.00"
    assert audit_failure.action_correct is True
    assert timeout.executed_tools == []


def test_case_filter_and_failure_isolation_for_missing_case() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)

    report = AgentEvaluationRunner().run_dataset(
        benchmark,
        mode=EvaluationMode.SCRIPTED,
        case_id="does-not-exist",
    )

    assert report.case_count == 0
    assert report.failed == 0
