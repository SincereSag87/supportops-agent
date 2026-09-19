from collections import Counter

from app.evaluation.models import AgentEvaluationCaseResult, AgentEvaluationReport, EvaluationMode


def _rate(values: list[bool]) -> float:
    if not values:
        return 1.0
    return round(sum(1 for item in values if item) / len(values), 4)


def build_report(
    benchmark_name: str,
    mode: EvaluationMode,
    model: str | None,
    results: list[AgentEvaluationCaseResult],
) -> AgentEvaluationReport:
    failures = Counter()
    for result in results:
        for check in result.failed_checks:
            failures[check] += 1
        if result.error:
            failures["error"] += 1

    max_or_loop = 0
    for result in results:
        failed_text = " ".join(result.failed_checks).lower()
        error_text = (result.error or "").lower()
        if "maximum" in failed_text or "loop" in failed_text:
            max_or_loop += 1
        elif "maximum" in error_text or "repeated" in error_text:
            max_or_loop += 1
    return AgentEvaluationReport(
        benchmark_name=benchmark_name,
        mode=mode,
        model=model,
        case_count=len(results),
        passed=sum(1 for result in results if result.success),
        failed=sum(1 for result in results if not result.success),
        task_success_rate=_rate([result.success for result in results]),
        tool_selection_accuracy=_rate(
            [
                not result.forbidden_tools_used
                and "missing tools" not in " ".join(result.failed_checks)
                for result in results
            ]
        ),
        policy_accuracy=_rate(
            [
                result.expected_policy_decision is None
                or result.expected_policy_decision == result.actual_policy_decision
                for result in results
            ]
        ),
        approval_accuracy=_rate([result.approval_correct for result in results]),
        action_safety_accuracy=_rate([result.action_correct for result in results]),
        final_state_accuracy=_rate([result.final_state_correct for result in results]),
        escalation_accuracy=_rate(
            [
                "escalation" not in result.failed_checks
                for result in results
            ]
        ),
        audit_completeness_rate=_rate([result.audit_complete for result in results]),
        failure_recovery_rate=_rate(
            [result.failure_recovered for result in results if "failure" in result.case_id]
        ),
        structured_parse_success_rate=_rate([result.parse_success for result in results]),
        average_steps=round(
            sum(result.step_count for result in results) / len(results) if results else 0,
            2,
        ),
        average_latency_ms=round(
            sum(result.latency_ms for result in results) / len(results) if results else 0,
            2,
        ),
        max_step_or_loop_failure_count=max_or_loop,
        failure_categories=dict(failures),
        cases=results,
    )
