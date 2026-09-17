import json
import re

from pydantic import ValidationError

from app.agent.decisions import AgentDecision


class AgentDecisionParseError(RuntimeError):
    """Raised when an LLM response cannot be parsed as a valid agent decision."""


FENCED_JSON_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def parse_agent_decision(raw_content: str) -> AgentDecision:
    content = raw_content.strip()
    match = FENCED_JSON_PATTERN.match(content)
    if match:
        content = match.group(1).strip()

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AgentDecisionParseError("LLM output was not valid JSON") from exc

    if not isinstance(payload, dict):
        raise AgentDecisionParseError("LLM decision JSON must be an object")

    try:
        return AgentDecision.model_validate(payload)
    except ValidationError as exc:
        raise AgentDecisionParseError(f"LLM decision failed validation: {exc}") from exc
