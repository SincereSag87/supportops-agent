from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.agent.models import AgentStatus
from app.audit.models import AuditEventType
from app.policies.models import ApprovalStatus, PolicyDecision


class EvaluationMode(StrEnum):
    SCRIPTED = "scripted"
    LIVE = "live"


class FailureInjectionType(StrEnum):
    MALFORMED_JSON = "malformed_json"
    MALFORMED_JSON_TWICE = "malformed_json_twice"
    LLM_TIMEOUT = "llm_timeout"
    LLM_UNAVAILABLE = "llm_unavailable"
    UNKNOWN_TOOL = "unknown_tool"
    INVALID_TOOL_ARGUMENTS = "invalid_tool_arguments"
    TOOL_DOMAIN_ERROR = "tool_domain_error"
    TOOL_UNEXPECTED_EXCEPTION = "tool_unexpected_exception"
    DUPLICATE_TOOL_LOOP = "duplicate_tool_loop"
    MAX_STEP_EXHAUSTION = "max_step_exhaustion"
    AUDIT_PRE_WRITE_FAILURE = "audit_pre_write_failure"
    ACTION_EXECUTION_FAILURE = "action_execution_failure"


class EvaluationFailureInjection(BaseModel):
    type: FailureInjectionType
    tool_name: str | None = None


class SupportAgentEvaluationCase(BaseModel):
    id: str
    description: str
    user_input: str
    customer_id: str | None = None
    model: str | None = None
    expected_status: AgentStatus
    expected_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    expected_policy_decision: PolicyDecision | None = None
    expected_approval_required: bool | None = None
    expected_approval_status: ApprovalStatus | None = None
    approval_decision: bool | None = None
    expected_escalated: bool = False
    expected_order_id: str | None = None
    expected_refund_amount: str | None = None
    expected_ticket_created: bool | None = None
    expected_final_contains: list[str] = Field(default_factory=list)
    expected_audit_events: list[AuditEventType] = Field(default_factory=list)
    max_steps: int | None = None
    scripted_decisions: list[str] = Field(default_factory=list)
    failure_injection: EvaluationFailureInjection | None = None

    @field_validator("expected_tools", "forbidden_tools")
    @classmethod
    def validate_tool_names(cls, value: list[str]) -> list[str]:
        if any(not item for item in value):
            raise ValueError("tool names must be non-empty")
        return value


class SupportAgentBenchmark(BaseModel):
    name: str
    description: str
    cases: list[SupportAgentEvaluationCase]

    @model_validator(mode="after")
    def validate_cases(self) -> "SupportAgentBenchmark":
        if not self.cases:
            raise ValueError("benchmark must include at least one case")
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("benchmark case ids must be unique")
        return self

    @classmethod
    def from_file(cls, path: str | Path) -> "SupportAgentBenchmark":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


class AgentEvaluationCaseResult(BaseModel):
    case_id: str
    mode: EvaluationMode
    model: str | None = None
    success: bool
    expected_status: AgentStatus
    actual_status: AgentStatus | None = None
    expected_tools: list[str] = Field(default_factory=list)
    actual_tools: list[str] = Field(default_factory=list)
    executed_tools: list[str] = Field(default_factory=list)
    forbidden_tools_used: list[str] = Field(default_factory=list)
    expected_policy_decision: PolicyDecision | None = None
    actual_policy_decision: PolicyDecision | None = None
    approval_correct: bool = True
    action_correct: bool = True
    final_state_correct: bool = True
    final_response_correct: bool = True
    audit_complete: bool = True
    step_count: int = 0
    latency_ms: int = 0
    failure_recovered: bool = False
    parse_success: bool = True
    refund_total: str | None = None
    ticket_count: int | None = None
    ticket_count_delta: int | None = None
    approval_status: ApprovalStatus | None = None
    final_response: str = ""
    failed_checks: list[str] = Field(default_factory=list)
    error: str | None = None


class AgentEvaluationReport(BaseModel):
    benchmark_name: str
    mode: EvaluationMode
    model: str | None = None
    case_count: int
    passed: int
    failed: int
    task_success_rate: float
    tool_selection_accuracy: float
    policy_accuracy: float
    approval_accuracy: float
    action_safety_accuracy: float
    final_state_accuracy: float
    escalation_accuracy: float
    audit_completeness_rate: float
    failure_recovery_rate: float
    structured_parse_success_rate: float
    average_steps: float
    average_latency_ms: float
    max_step_or_loop_failure_count: int
    failure_categories: dict[str, int] = Field(default_factory=dict)
    cases: list[AgentEvaluationCaseResult]

    def to_json_file(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.model_dump_json(indent=2), encoding="utf-8")


def decision_json(**payload: Any) -> str:
    import json

    return json.dumps(payload)
