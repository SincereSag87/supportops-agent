from openai import APIConnectionError, NotFoundError, OpenAI

from app.core.config import Settings
from app.llm.base import (
    LLMEmptyResponseError,
    LLMMalformedResponseError,
    LLMModelNotFoundError,
    LLMProvider,
    LLMUnavailableError,
)
from app.llm.models import ChatMessage, ChatResponse


class OllamaProvider(LLMProvider):
    """OpenAI-compatible provider for local Ollama chat completions."""

    provider_name = "ollama"

    def __init__(self, settings: Settings, client: OpenAI | None = None) -> None:
        self.settings = settings
        self.client = client or OpenAI(base_url=settings.ollama_base_url, api_key="ollama")

    def generate(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse:
        selected_model = model or self.settings.default_model
        try:
            completion = self.client.chat.completions.create(
                model=selected_model,
                messages=[message.as_openai_message() for message in messages],
            )
        except APIConnectionError as exc:
            raise LLMUnavailableError("Ollama is unavailable or refused the connection") from exc
        except NotFoundError as exc:
            raise LLMModelNotFoundError(f"Model not found: {selected_model}") from exc
        except Exception as exc:
            raise LLMUnavailableError("Ollama request failed") from exc

        try:
            choice = completion.choices[0]
            content = choice.message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMMalformedResponseError("Ollama returned a malformed response") from exc

        if content is None or not content.strip():
            raise LLMEmptyResponseError("Ollama returned an empty response")

        return ChatResponse(
            content=content.strip(),
            model=selected_model,
            provider=self.provider_name,
        )
