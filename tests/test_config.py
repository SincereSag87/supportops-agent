from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.ollama_base_url == "http://localhost:11434/v1"
    assert settings.default_model == "llama3.2"
    assert settings.agent_max_steps == 8
    assert settings.auto_action_limit == Decimal("100.00")
    assert settings.approval_action_limit == Decimal("500.00")


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEFAULT_MODEL", "gemma3")
    monkeypatch.setenv("AGENT_MAX_STEPS", "4")
    monkeypatch.setenv("AUTO_ACTION_LIMIT", "25.50")
    monkeypatch.setenv("APPROVAL_ACTION_LIMIT", "250.75")

    settings = Settings(_env_file=None)

    assert settings.default_model == "gemma3"
    assert settings.agent_max_steps == 4
    assert settings.auto_action_limit == Decimal("25.50")
    assert settings.approval_action_limit == Decimal("250.75")


def test_settings_policy_threshold_validation() -> None:
    with pytest.raises(ValidationError):
        Settings(
            AUTO_ACTION_LIMIT=Decimal("500.00"),
            APPROVAL_ACTION_LIMIT=Decimal("100.00"),
            _env_file=None,
        )


def test_settings_max_steps_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(AGENT_MAX_STEPS=0, _env_file=None)
