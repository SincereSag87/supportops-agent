from pydantic import BaseModel

from app.core.config import Settings
from app.llm.models import ChatMessage, ChatRole
from app.llm.ollama_provider import OllamaProvider
from app.tools.registry import ToolRegistry


class HealthReport(BaseModel):
    status: str
    ollama_reachable: bool
    configured_model: str
    registered_tool_count: int


class HealthService:
    def __init__(
        self,
        settings: Settings,
        tool_registry: ToolRegistry,
        llm_provider: OllamaProvider | None = None,
    ) -> None:
        self.settings = settings
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider or OllamaProvider(settings)

    def check(self) -> HealthReport:
        ollama_reachable = self._check_ollama()
        return HealthReport(
            status="ready",
            ollama_reachable=ollama_reachable,
            configured_model=self.settings.default_model,
            registered_tool_count=len(self.tool_registry.list_tools()),
        )

    def _check_ollama(self) -> bool:
        try:
            self.llm_provider.generate(
                [ChatMessage(role=ChatRole.USER, content="Reply with OK for a health check.")],
                model=self.settings.default_model,
            )
        except Exception:
            return False
        return True
