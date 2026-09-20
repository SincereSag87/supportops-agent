from typing import Any

from pydantic import BaseModel


class MetricsSnapshot(BaseModel):
    requests: dict[str, Any]
    agent: dict[str, Any]
    tools: dict[str, Any]
    policy: dict[str, Any]
    approvals: dict[str, Any]
    actions: dict[str, Any]
    evaluation: dict[str, Any]
    safety: dict[str, Any]
    errors: dict[str, int]
