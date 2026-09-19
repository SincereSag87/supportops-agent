from decimal import Decimal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    default_model: str = Field(default="llama3.2", alias="DEFAULT_MODEL")
    agent_max_steps: int = Field(default=8, alias="AGENT_MAX_STEPS")
    agent_max_context_chars: int = Field(default=16000, alias="AGENT_MAX_CONTEXT_CHARS")
    agent_max_identical_tool_calls: int = Field(
        default=2, alias="AGENT_MAX_IDENTICAL_TOOL_CALLS"
    )
    agent_allow_low_risk_writes: bool = Field(
        default=True, alias="AGENT_ALLOW_LOW_RISK_WRITES"
    )
    agent_decision_repair_attempts: int = Field(default=1, alias="AGENT_DECISION_REPAIR_ATTEMPTS")
    llm_timeout_seconds: float = Field(default=90, alias="LLM_TIMEOUT_SECONDS")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: str = Field(
        default="http://localhost:7860,http://127.0.0.1:7860",
        alias="CORS_ORIGINS",
    )
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

    @field_validator("agent_max_context_chars", "agent_max_identical_tool_calls")
    @classmethod
    def validate_positive_agent_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("agent limits must be greater than 0")
        return value

    @field_validator("agent_decision_repair_attempts")
    @classmethod
    def validate_non_negative_repair_attempts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("AGENT_DECISION_REPAIR_ATTEMPTS must be greater than or equal to 0")
        return value

    @field_validator("llm_timeout_seconds")
    @classmethod
    def validate_llm_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS must be greater than 0")
        return value

    @field_validator("api_port")
    @classmethod
    def validate_api_port(cls, value: int) -> int:
        if value <= 0 or value > 65535:
            raise ValueError("API_PORT must be a valid TCP port")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

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
