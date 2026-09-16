from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str
    timestamp: datetime | None = None

    def as_openai_message(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
