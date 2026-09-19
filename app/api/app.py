from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import add_exception_handlers
from app.api.routes import agent, approvals, audit, demo, evaluation, health, support
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SupportOps Agent",
        description=(
            "Local-first AI support operations agent with policy enforcement, "
            "human approval, auditability, and deterministic agent evaluation."
        ),
        version="0.1.0-development",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    add_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(support.router)
    app.include_router(agent.router)
    app.include_router(approvals.router)
    app.include_router(audit.router)
    app.include_router(evaluation.router)
    app.include_router(demo.router)
    return app


app = create_app()
