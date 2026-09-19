from app.llm.base import LLMProvider, LLMProviderError, LLMUnavailableError
from app.llm.models import ChatMessage, ChatResponse


class ScriptedLLMProvider(LLMProvider):
    """Evaluation provider that returns deterministic outputs or injected failures."""

    def __init__(self, responses: list[str], *, fail_with: str | None = None) -> None:
        self.responses = list(responses)
        self.fail_with = fail_with
        self.call_count = 0

    def generate(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse:
        self.call_count += 1
        if self.fail_with == "timeout":
            raise LLMUnavailableError("LLM request timed out")
        if self.fail_with == "unavailable":
            raise LLMProviderError("LLM is unavailable")
        if not self.responses:
            raise LLMProviderError("No scripted response available")
        return ChatResponse(
            content=self.responses.pop(0),
            model=model or "scripted",
            provider="scripted",
        )
