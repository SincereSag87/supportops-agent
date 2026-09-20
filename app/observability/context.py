from contextvars import ContextVar
from uuid import uuid4

_http_request_id: ContextVar[str | None] = ContextVar("http_request_id", default=None)


def generate_request_id() -> str:
    return str(uuid4())


def get_http_request_id() -> str | None:
    return _http_request_id.get()


def set_http_request_id(request_id: str):
    return _http_request_id.set(request_id)


def reset_http_request_id(token) -> None:
    _http_request_id.reset(token)


def is_safe_request_id(value: str | None) -> bool:
    if not value:
        return False
    if len(value) > 128:
        return False
    return all(char.isalnum() or char in {"-", "_", "."} for char in value)
