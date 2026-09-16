from decimal import Decimal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    default_model: str = Field(default="llama3.2", alias="DEFAULT_MODEL")
    agent_max_steps: int = Field(default=8, alias="AGENT_MAX_STEPS")
    auto_action_limit: Decimal = Field(default=Decimal("100.00"), alias="AUTO_ACTION_LIMIT")
    approval_action_limit: Decimal = Field(
        default=Decimal("500.00"), alias="APPROVAL_ACTION_LIMIT"
    )

    @field_validator("agent_max_steps")
    @classmethod
    def validate_agent_max_steps(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("AGENT_MAX_STEPS must be greater than 0")
        return value

    @field_validator("auto_action_limit", "approval_action_limit")
    @classmethod
    def validate_money_thresholds(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError("policy thresholds must be greater than or equal to 0")
        return value

    @field_validator("approval_action_limit")
    @classmethod
    def validate_approval_limit(cls, value: Decimal, info) -> Decimal:
        auto_limit = info.data.get("auto_action_limit")
        if auto_limit is not None and value < auto_limit:
            raise ValueError(
                "APPROVAL_ACTION_LIMIT must be greater than or equal to AUTO_ACTION_LIMIT"
            )
        return value


def get_settings() -> Settings:
    return Settings()
