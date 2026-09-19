from pathlib import Path

from fastapi import APIRouter

from app.api.errors import error_response
from app.api.models import EvaluationRequestAPI
from app.evaluation.models import EvaluationMode, SupportAgentBenchmark
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

BENCHMARK_REGISTRY = {
    "support-agent-demo": Path("benchmarks/support_agent_eval.json"),
}


@router.get("/benchmarks")
def list_benchmarks() -> list[dict[str, object]]:
    benchmarks = []
    for benchmark_id, path in BENCHMARK_REGISTRY.items():
        benchmark = SupportAgentBenchmark.from_file(path)
        benchmarks.append(
            {
                "benchmark_id": benchmark_id,
                "name": benchmark.name,
                "description": benchmark.description,
                "cases": [
                    {"id": case.id, "description": case.description}
                    for case in benchmark.cases
                ],
            }
        )
    return benchmarks


@router.post("/run")
def run_evaluation(request: EvaluationRequestAPI):
    path = BENCHMARK_REGISTRY.get(request.benchmark)
    if path is None:
        return error_response(404, "BENCHMARK_NOT_FOUND", "Unknown benchmark id.")
    try:
        mode = EvaluationMode(request.mode)
    except ValueError:
        return error_response(422, "INVALID_EVALUATION_MODE", "Use scripted or live.")
    report = EvaluationService().run(
        path,
        mode=mode,
        model=request.model,
        case_id=request.case_id,
    )
    return {
        "cases": report.case_count,
        "passed": report.passed,
        "failed": report.failed,
        "task_success_rate": report.task_success_rate,
        "tool_selection_accuracy": report.tool_selection_accuracy,
        "policy_accuracy": report.policy_accuracy,
        "approval_accuracy": report.approval_accuracy,
        "action_safety_accuracy": report.action_safety_accuracy,
        "final_state_accuracy": report.final_state_accuracy,
        "audit_completeness": report.audit_completeness_rate,
        "failure_recovery_rate": report.failure_recovery_rate,
        "parse_success_rate": report.structured_parse_success_rate,
        "average_steps": report.average_steps,
        "average_latency_ms": report.average_latency_ms,
        "failed_cases": [
            case.model_dump(mode="json") for case in report.cases if not case.success
        ],
    }
