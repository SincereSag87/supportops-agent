from dataclasses import dataclass
from typing import Any


@dataclass
class UIResult:
    message: str
    data: Any = None


class UIClientError(RuntimeError):
    """Friendly UI-facing API client error."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
