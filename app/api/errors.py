from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.approvals.repository import ApprovalNotFoundError
from app.approvals.service import (
    ApprovalActionMismatchError,
    ApprovalConsumedError,
    ApprovalDeniedError,
    ApprovalRequiredError,
)
from app.llm.base import LLMModelNotFoundError, LLMProviderError, LLMUnavailableError
from app.repositories.base import (
    CustomerNotFoundError,
    OrderNotFoundError,
    RefundNotFoundError,
    SupportDomainError,
    TicketNotFoundError,
)
from app.services.action_service import ActionExecutionError, ActionNotAllowedError


def _record_error_metric(request: Request, key: str) -> None:
    try:
        from app.api.dependencies import get_container

        get_container().metrics_store.increment(f"errors.{key}")
        if key == "approvalconsumederror":
            get_container().metrics_store.increment("approvals.replay_blocks")
            get_container().metrics_store.increment("safety.unauthorized_action_blocks")
    except Exception:
        return


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CustomerNotFoundError)
    @app.exception_handler(OrderNotFoundError)
    @app.exception_handler(TicketNotFoundError)
    @app.exception_handler(RefundNotFoundError)
    @app.exception_handler(ApprovalNotFoundError)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "not_found")
        return error_response(404, "NOT_FOUND", str(exc))

    @app.exception_handler(ApprovalDeniedError)
    @app.exception_handler(ApprovalConsumedError)
    @app.exception_handler(ApprovalActionMismatchError)
    @app.exception_handler(ApprovalRequiredError)
    async def approval_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, exc.__class__.__name__.lower())
        return error_response(409, exc.__class__.__name__.upper(), str(exc))

    @app.exception_handler(ActionNotAllowedError)
    async def action_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "action_not_allowed")
        return error_response(403, "ACTION_NOT_ALLOWED", str(exc))

    @app.exception_handler(ActionExecutionError)
    async def action_execution_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "action_execution_failed")
        return error_response(409, "ACTION_EXECUTION_FAILED", str(exc))

    @app.exception_handler(LLMModelNotFoundError)
    async def model_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "model_not_available")
        return error_response(
            503,
            "MODEL_NOT_AVAILABLE",
            "The requested local model is not available.",
        )

    @app.exception_handler(LLMUnavailableError)
    async def llm_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "llm_unavailable")
        return error_response(503, "LLM_UNAVAILABLE", str(exc))

    @app.exception_handler(LLMProviderError)
    async def llm_error_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "llm_provider_error")
        return error_response(502, "LLM_PROVIDER_ERROR", str(exc))

    @app.exception_handler(SupportDomainError)
    async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "domain_error")
        return error_response(422, "DOMAIN_ERROR", str(exc))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        _record_error_metric(request, "internal_server_error")
        return error_response(500, "INTERNAL_SERVER_ERROR", "Unexpected server error.")
