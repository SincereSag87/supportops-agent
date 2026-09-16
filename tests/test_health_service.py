from app.core.config import Settings
from app.llm.models import ChatResponse
from app.services.health_service import HealthService
from app.tools.demo import EchoTool
from app.tools.registry import ToolRegistry


class HealthyProvider:
    def generate(self, messages, model=None):
        return ChatResponse(content="OK", model=model or "llama3.2", provider="test")


class UnavailableProvider:
    def generate(self, messages, model=None):
        raise RuntimeError("offline")


def test_health_service_healthy_ollama() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    service = HealthService(Settings(_env_file=None), registry, HealthyProvider())

    health = service.check()

    assert health.status == "ready"
    assert health.ollama_reachable is True
    assert health.configured_model == "llama3.2"
    assert health.registered_tool_count == 1


def test_health_service_unavailable_ollama() -> None:
    service = HealthService(Settings(_env_file=None), ToolRegistry(), UnavailableProvider())

    health = service.check()

    assert health.status == "ready"
    assert health.ollama_reachable is False
    assert health.registered_tool_count == 0
