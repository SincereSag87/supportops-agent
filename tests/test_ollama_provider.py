from types import SimpleNamespace

import pytest
from openai import APIConnectionError, NotFoundError

from app.core.config import Settings
from app.llm.base import LLMEmptyResponseError, LLMModelNotFoundError, LLMUnavailableError
from app.llm.models import ChatMessage, ChatRole
from app.llm.ollama_provider import OllamaProvider


class FakeNotFoundError(NotFoundError):
    def __init__(self) -> None:
        Exception.__init__(self, "not found")


class FakeCompletions:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, completions: FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


def completion(content: str | None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_ollama_provider_successful_generation() -> None:
    completions = FakeCompletions(response=completion("Hello from Ollama"))
    provider = OllamaProvider(Settings(_env_file=None), client=FakeClient(completions))

    response = provider.generate([ChatMessage(role=ChatRole.USER, content="Hi")])

    assert response.content == "Hello from Ollama"
    assert response.model == "llama3.2"
    assert response.provider == "ollama"


def test_ollama_provider_model_override() -> None:
    completions = FakeCompletions(response=completion("Gemma response"))
    provider = OllamaProvider(Settings(_env_file=None), client=FakeClient(completions))

    response = provider.generate([ChatMessage(role=ChatRole.USER, content="Hi")], model="gemma3")

    assert response.model == "gemma3"
    assert completions.calls[0]["model"] == "gemma3"


def test_ollama_provider_unavailable() -> None:
    request = SimpleNamespace(method="POST", url="http://localhost")
    completions = FakeCompletions(error=APIConnectionError(request=request))
    provider = OllamaProvider(Settings(_env_file=None), client=FakeClient(completions))

    with pytest.raises(LLMUnavailableError):
        provider.generate([ChatMessage(role=ChatRole.USER, content="Hi")])


def test_ollama_provider_model_not_found() -> None:
    completions = FakeCompletions(error=FakeNotFoundError())
    provider = OllamaProvider(Settings(_env_file=None), client=FakeClient(completions))

    with pytest.raises(LLMModelNotFoundError):
        provider.generate([ChatMessage(role=ChatRole.USER, content="Hi")], model="missing")


def test_ollama_provider_empty_response() -> None:
    completions = FakeCompletions(response=completion("   "))
    provider = OllamaProvider(Settings(_env_file=None), client=FakeClient(completions))

    with pytest.raises(LLMEmptyResponseError):
        provider.generate([ChatMessage(role=ChatRole.USER, content="Hi")])
