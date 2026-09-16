from abc import ABC, abstractmethod

from app.llm.models import ChatMessage, ChatResponse


class LLMProviderError(RuntimeError):
    """Base error for clean LLM provider failures."""


class LLMUnavailableError(LLMProviderError):
    """Raised when the configured LLM service cannot be reached."""


class LLMModelNotFoundError(LLMProviderError):
    """Raised when the requested model is not available."""


class LLMEmptyResponseError(LLMProviderError):
    """Raised when the provider returns no usable content."""


class LLMMalformedResponseError(LLMProviderError):
    """Raised when the provider response shape is not usable."""


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse:
        """Generate a response for chat messages."""
