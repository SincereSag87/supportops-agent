import argparse

from app.core.config import get_settings
from app.llm.base import LLMProviderError
from app.llm.models import ChatMessage, ChatRole
from app.llm.ollama_provider import OllamaProvider
from app.services.health_service import HealthService
from app.tools.demo import EchoTool, EchoToolInput
from app.tools.registry import ToolRegistry


def build_registry(include_demo_tools: bool = False) -> ToolRegistry:
    registry = ToolRegistry()
    if include_demo_tools:
        registry.register(EchoTool())
    return registry


def print_health(include_demo_tools: bool = False) -> int:
    settings = get_settings()
    registry = build_registry(include_demo_tools=include_demo_tools)
    health = HealthService(settings=settings, tool_registry=registry).check()
    ollama_status = "reachable" if health.ollama_reachable else "unavailable"
    print("SupportOps Agent")
    print(f"Status: {health.status}")
    print(f"Ollama: {ollama_status}")
    print(f"Model: {health.configured_model}")
    print(f"Registered tools: {health.registered_tool_count}")
    return 0


def run_llm_test(model: str | None = None) -> int:
    settings = get_settings()
    provider = OllamaProvider(settings)
    prompt = (
        "Explain in three sentences why an AI agent should require human approval before "
        "high-risk actions."
    )
    try:
        response = provider.generate([ChatMessage(role=ChatRole.USER, content=prompt)], model=model)
    except LLMProviderError as exc:
        print(f"LLM test failed: {exc}")
        return 1
    print(response.content)
    return 0


def list_tools(include_demo_tools: bool = False) -> int:
    registry = build_registry(include_demo_tools=include_demo_tools)
    print("Name\tRisk\tDescription")
    for tool in registry.list_tools():
        print(f"{tool.name}\t{tool.risk_level.value}\t{tool.description}")
    return 0


def run_tool_test(tool_name: str) -> int:
    registry = build_registry(include_demo_tools=True)
    if tool_name != "echo":
        print("Only the explicit test/demo echo tool can be run from this command.")
        return 1
    tool = registry.get(tool_name)
    result = tool.execute(EchoToolInput(message="SupportOps Agent demo tool check"))
    print(result.model_dump_json())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SupportOps Agent Phase 1 CLI")
    parser.add_argument("--llm-test", action="store_true", help="Run a safe LLM smoke prompt")
    parser.add_argument("--model", help="Override the configured LLM model")
    parser.add_argument("--list-tools", action="store_true", help="List registered tools")
    parser.add_argument(
        "--tool-test",
        choices=["echo"],
        help="Run an explicit demo tool smoke test",
    )
    parser.add_argument(
        "--include-demo-tools",
        action="store_true",
        help="Include internal test/demo tools in registry output",
    )
    args = parser.parse_args()

    if args.llm_test:
        return run_llm_test(model=args.model)
    if args.list_tools:
        return list_tools(include_demo_tools=args.include_demo_tools)
    if args.tool_test:
        return run_tool_test(args.tool_test)
    return print_health(include_demo_tools=args.include_demo_tools)


if __name__ == "__main__":
    raise SystemExit(main())
