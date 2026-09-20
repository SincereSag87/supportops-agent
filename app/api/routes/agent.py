from fastapi import APIRouter, Depends

from app.api.dependencies import ServiceContainer, get_container
from app.api.errors import error_response
from app.api.models import AgentRequestAPI, serialize_agent_result
from app.observability.tracing import timer

router = APIRouter(prefix="/agent", tags=["agent"])
ContainerDep = Depends(get_container)


@router.post("/requests")
def create_agent_request(
    request: AgentRequestAPI,
    container: ServiceContainer = ContainerDep,
):
    with timer() as elapsed_ms:
        result = container.agent_service.handle_request(
            request.user_input,
            customer_id=request.customer_id,
            model=request.model,
        )
    record_agent_metrics(container, result, request.model, elapsed_ms())
    if result.error:
        error_text = result.error.lower()
        if "model not found" in error_text:
            container.metrics_store.increment("errors.model_not_available")
            return error_response(
                503,
                "MODEL_NOT_AVAILABLE",
                "The requested local model is not available.",
            )
        if "timed out" in error_text or "unavailable" in error_text:
            container.metrics_store.increment("errors.llm_unavailable")
            return error_response(503, "LLM_UNAVAILABLE", result.error)
        if "valid next decision" in result.response.lower() or "json" in error_text:
            container.metrics_store.increment("agent.structured_parse_failures")
            return error_response(502, "AGENT_DECISION_PARSE_FAILED", result.error)
    return serialize_agent_result(result)


def record_agent_metrics(
    container: ServiceContainer,
    result,
    model: str | None,
    duration_ms: float,
) -> None:
    metrics = container.metrics_store
    metrics.increment("agent.requests")
    metrics.increment(f"agent.{result.status.value}")
    metrics.count_model(model)
    metrics.observe("agent.latency_ms", duration_ms)
    metrics.observe("agent.steps", len(result.decision_history))
    for call in result.tool_calls:
        metrics.count_tool_usage(call.tool_name)
        if call.tool_name in {"issue_refund", "reverse_refund"}:
            metrics.increment("tools.high_risk_proposals")
    for tool_result in result.tool_results:
        metrics.count_tool_usage(tool_result.tool_name, success=tool_result.success)
        if tool_result.success and tool_result.tool_name == "issue_refund":
            metrics.increment("actions.refunds_executed")
            metrics.increment("tools.high_risk_executions")
        if tool_result.success and tool_result.tool_name == "reverse_refund":
            metrics.increment("actions.reversals_executed")
            metrics.increment("tools.high_risk_executions")
    for approval in result.approvals_required:
        metrics.increment("approvals.requests")
        if approval.policy_decision:
            metrics.increment(f"policy.{approval.policy_decision.decision.value}")
    if result.escalated:
        metrics.increment("policy.escalate")
