from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app import __version__
from app.api.dependencies import get_container
from app.api.errors import add_exception_handlers
from app.api.routes import agent, approvals, audit, demo, evaluation, health, metrics, support
from app.core.config import get_settings
from app.observability.context import (
    generate_request_id,
    is_safe_request_id,
    reset_http_request_id,
    set_http_request_id,
)
from app.observability.logging import configure_logging, get_logger, safe_extra

logger = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format, settings.log_file)
    app = FastAPI(
        title="SupportOps Agent",
        description=(
            "Local-first AI support operations agent with policy enforcement, "
            "human approval, auditability, and deterministic agent evaluation."
        ),
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    add_request_observability(app)
    add_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(support.router)
    app.include_router(agent.router)
    app.include_router(approvals.router)
    app.include_router(audit.router)
    app.include_router(evaluation.router)
    app.include_router(demo.router)
    app.include_router(metrics.router)
    return app


def add_request_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_observability(request: Request, call_next) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        request_id = incoming_id if is_safe_request_id(incoming_id) else generate_request_id()
        token = set_http_request_id(request_id)
        start = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((perf_counter() - start) * 1000, 2)
            try:
                response.headers["X-Request-ID"] = request_id
            except UnboundLocalError:
                pass
            container = get_container()
            metrics_store = container.metrics_store
            metrics_store.increment("requests.total")
            metrics_store.observe("requests.latency_ms", duration_ms)
            if status_code < 400:
                metrics_store.increment("requests.successful")
            else:
                metrics_store.increment("requests.failed")
                metrics_store.increment(f"errors.http_{status_code}")
            logger.info(
                "http_request",
                extra=safe_extra(
                    http_request_id=request_id,
                    endpoint=request.url.path,
                    operation=request.method,
                    duration_ms=duration_ms,
                    success=status_code < 400,
                    error_category=f"http_{status_code}" if status_code >= 400 else None,
                ),
            )
            reset_http_request_id(token)


app = create_app()
