from app.evaluation.models import AgentEvaluationReport


def format_report(report: AgentEvaluationReport) -> str:
    lines = [
        f"Benchmark: {report.benchmark_name}",
        f"Mode: {report.mode.value}",
        f"Model: {report.model or 'scripted'}",
        f"Cases: {report.case_count}",
        f"Passed: {report.passed}",
        "",
        "Metrics",
        f"Task Success Rate: {report.task_success_rate:.2%}",
        f"Tool Selection Accuracy: {report.tool_selection_accuracy:.2%}",
        f"Policy Accuracy: {report.policy_accuracy:.2%}",
        f"Approval Accuracy: {report.approval_accuracy:.2%}",
        f"Action Safety Accuracy: {report.action_safety_accuracy:.2%}",
        f"Final State Accuracy: {report.final_state_accuracy:.2%}",
        f"Audit Completeness: {report.audit_completeness_rate:.2%}",
        f"Failure Recovery: {report.failure_recovery_rate:.2%}",
        f"Structured Parse Success: {report.structured_parse_success_rate:.2%}",
        f"Average Steps: {report.average_steps}",
        f"Average Latency ms: {report.average_latency_ms}",
    ]
    failed = [case for case in report.cases if not case.success]
    if failed:
        lines.extend(["", "Failed Cases"])
        for case in failed:
            policy = case.actual_policy_decision.value if case.actual_policy_decision else "none"
            approval = case.approval_status.value if case.approval_status else "none"
            final_state = (
                f"refund_total={case.refund_total}, "
                f"ticket_delta={case.ticket_count_delta}"
            )
            lines.extend(
                [
                    f"Case: {case.case_id}",
                    f"Expected: {case.expected_status.value}",
                    f"Actual: {case.actual_status.value if case.actual_status else 'none'}",
                    f"Failed checks: {', '.join(case.failed_checks) or 'none'}",
                    f"Tool history: proposed={case.actual_tools}; executed={case.executed_tools}",
                    f"Policy: {policy}",
                    f"Approval: {approval}",
                    f"Final state: {final_state}",
                    f"Error: {case.error or 'none'}",
                    "",
                ]
            )
    return "\n".join(lines)
