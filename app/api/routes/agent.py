from fastapi import APIRouter, Depends

from app.api.dependencies import ServiceContainer, get_container
from app.api.errors import error_response
from app.api.models import AgentRequestAPI, serialize_agent_result

router = APIRouter(prefix="/agent", tags=["agent"])
ContainerDep = Depends(get_container)


@router.post("/requests")
def create_agent_request(
    request: AgentRequestAPI,
    container: ServiceContainer = ContainerDep,
):
    result = container.agent_service.handle_request(
        request.user_input,
        customer_id=request.customer_id,
        model=request.model,
    )
    if result.error:
        error_text = result.error.lower()
        if "model not found" in error_text:
            return error_response(
                503,
                "MODEL_NOT_AVAILABLE",
                "The requested local model is not available.",
            )
        if "timed out" in error_text or "unavailable" in error_text:
            return error_response(503, "LLM_UNAVAILABLE", result.error)
        if "valid next decision" in result.response.lower() or "json" in error_text:
            return error_response(502, "AGENT_DECISION_PARSE_FAILED", result.error)
    return serialize_agent_result(result)
