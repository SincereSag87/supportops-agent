import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.observability.context import get_http_request_id

SAFE_LOG_FIELDS = {
    "http_request_id",
    "agent_request_id",
    "endpoint",
    "operation",
    "agent_status",
    "model",
    "customer_id",
    "order_id",
    "tool_name",
    "tool_risk",
    "policy_decision",
    "approval_id",
    "approval_status",
    "audit_event_type",
    "step_count",
    "duration_ms",
    "success",
    "error_category",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for field in SAFE_LOG_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if "http_request_id" not in payload and get_http_request_id():
            payload["http_request_id"] = get_http_request_id()
        return json.dumps(payload, default=str, sort_keys=True)


def configure_logging(level: str = "INFO", log_format: str = "json", log_file: str = "") -> None:
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(level.upper())
    handler: logging.Handler
    if log_file:
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


def get_logger(name: str = "supportops") -> logging.Logger:
    return logging.getLogger(name)


def safe_extra(**fields: Any) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if key in SAFE_LOG_FIELDS}
