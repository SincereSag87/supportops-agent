from __future__ import annotations

from time import perf_counter

from pydantic import BaseModel

from app.agent.models import AgentStatus
from app.agent.runner import AgentRunner
from app.agent.safety import AgentSafetyController
from app.approvals.repository import InMemoryApprovalRepository
from app.approvals.service import ApprovalService
from app.audit.models import AuditEvent, AuditEventType
from app.audit.repository import InMemoryAuditRepository
from app.audit.service import AuditService
from app.core.config import Settings
from app.evaluation.assertions import evaluate_case_expectations
from app.evaluation.metrics import build_report
from app.evaluation.models import (
    AgentEvaluationCaseResult,
    AgentEvaluationReport,
    EvaluationFailureInjection,
    EvaluationMode,
    FailureInjectionType,
    SupportAgentBenchmark,
    SupportAgentEvaluationCase,
)
from app.evaluation.recovery import ScriptedLLMProvider
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.policies.engine import PolicyEngine
from app.policies.models import ApprovalStatus, PolicyDecision
from app.services.action_service import ActionService
from app.services.agent_service import AgentService
from app.support.service import SupportService, create_demo_support_service
from app.tools.base import Tool
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry
from app.tools.support_registry import create_support_tool_registry


class AuditFailure(RuntimeError):
    """Raised by evaluation-only audit fault injection."""


class FaultyAuditService(AuditService):
    def __init__(
        self,
        repository: InMemoryAuditRepository,
        *,
        fail_on_event: AuditEventType,
    ) -> None:
        super().__init__(repository)
        self.fail_on_event = fail_on_event

    def record(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        event_type = kwargs.get("event_type") if kwargs else None
        if event_type is None and len(args) > 1:
            event_type = args[1]
        if event_type == self.fail_on_event:
            raise AuditFailure(f"Injected audit failure for {self.fail_on_event.value}")
        return super().record(*args, **kwargs)


class FailingTool(Tool):
    def __init__(self, wrapped: Tool, *, unexpected: bool = False) -> None:
        self.wrapped = wrapped
        self.name = wrapped.name
        self.description = wrapped.description
        self.input_model = wrapped.input_model
        self.output_model = wrapped.output_model
        self.risk_level = wrapped.risk_level
        self.unexpected = unexpected

    def execute(self, tool_input: BaseModel) -> ToolResult:
        if self.unexpected:
            raise RuntimeError("Injected unexpected tool failure")
        validated = self.input_model.model_validate(tool_input)
        return ToolResult(
            call_id=getattr(validated, "call_id", None) or __import__("uuid").uuid4(),
            tool_name=self.name,
            success=False,
            error="Injected tool failure",
        )


class EvaluationEnvironment(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    support_service: SupportService
    registry: ToolRegistry
    approval_service: ApprovalService
    audit_service: AuditService
    action_service: ActionService
    policy_engine: PolicyEngine
    agent_service: AgentService


class AgentEvaluationRunner:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings(_env_file=None)

    def run_dataset(
        self,
        benchmark: SupportAgentBenchmark,
        *,
        mode: EvaluationMode = EvaluationMode.SCRIPTED,
        model: str | None = None,
        case_id: str | None = None,
        provider: LLMProvider | None = None,
    ) -> AgentEvaluationReport:
        cases = benchmark.cases
        if case_id is not None:
            cases = [case for case in cases if case.id == case_id]
        results: list[AgentEvaluationCaseResult] = []
        for case in cases:
            try:
                results.append(self.run_case(case, mode=mode, model=model, provider=provider))
            except Exception as exc:
                results.append(
                    AgentEvaluationCaseResult(
                        case_id=case.id,
                        mode=mode,
                        model=model or case.model,
                        success=False,
                        expected_status=case.expected_status,
                        error=f"Unexpected evaluation crash: {exc}",
                        failed_checks=["unexpected crash"],
                    )
                )
        return build_report(benchmark.name, mode, model, results)

    def run_case(
        self,
        case: SupportAgentEvaluationCase,
        *,
        mode: EvaluationMode,
        model: str | None,
        provider: LLMProvider | None = None,
    ) -> AgentEvaluationCaseResult:
        env = self._build_environment(case, mode, provider)
        starting_ticket_count = (
            len(env.support_service.get_customer_tickets(case.customer_id))
            if case.customer_id
            else None
        )
        start = perf_counter()
        agent_result = env.agent_service.handle_request(
            case.user_input,
            customer_id=case.customer_id,
            model=model or case.model,
        )
        approval_status: ApprovalStatus | None = None
        if agent_result.approvals_required:
            approval = agent_result.approvals_required[0]
            approval_status = approval.status
            if case.approval_decision is not None:
                resolved = env.agent_service.resolve_approval(
                    approval.approval_id,
                    approved=case.approval_decision,
                    decided_by="evaluation-manager",
                    comment="Evaluation decision.",
                )
                approval_status = env.approval_service.get(approval.approval_id).status
                if case.approval_decision:
                    agent_result = resolved.model_copy(
                        update={
                            "tool_calls": agent_result.tool_calls,
                            "tool_results": [*agent_result.tool_results, *resolved.tool_results],
                            "decision_history": agent_result.decision_history,
                        }
                    )
        latency_ms = int((perf_counter() - start) * 1000)

        events = env.audit_service.list_for_request(agent_result.request_id)
        result = self._build_case_result(
            case,
            mode,
            model,
            agent_result,
            events,
            env,
            latency_ms,
            starting_ticket_count,
        )
        if approval_status is not None:
            result.approval_status = approval_status
        return evaluate_case_expectations(case, result, events)

    def _build_environment(
        self,
        case: SupportAgentEvaluationCase,
        mode: EvaluationMode,
        provider: LLMProvider | None,
    ) -> EvaluationEnvironment:
        settings = self.settings
        if case.max_steps is not None:
            settings = Settings(AGENT_MAX_STEPS=case.max_steps, _env_file=None)
        support_service = create_demo_support_service()
        registry = create_support_tool_registry(support_service)
        self._apply_tool_faults(registry, case.failure_injection)
        audit_repo = InMemoryAuditRepository()
        audit_service: AuditService
        if (
            case.failure_injection
            and case.failure_injection.type == FailureInjectionType.AUDIT_PRE_WRITE_FAILURE
        ):
            audit_service = FaultyAuditService(
                audit_repo,
                fail_on_event=AuditEventType.TOOL_STARTED,
            )
        else:
            audit_service = AuditService(audit_repo)
        approval_service = ApprovalService(InMemoryApprovalRepository())
        action_service = ActionService(registry, approval_service, audit_service)
        policy_engine = PolicyEngine(support_service)
        llm_provider = provider or self._provider_for_case(case, mode, settings)
        runner = AgentRunner(
            llm_provider=llm_provider,
            tool_registry=registry,
            safety_controller=AgentSafetyController(settings),
            settings=settings,
            policy_engine=policy_engine,
            action_service=action_service,
            audit_service=audit_service,
        )
        agent_service = AgentService(
            runner,
            approval_service=approval_service,
            action_service=action_service,
            audit_service=audit_service,
        )
        return EvaluationEnvironment(
            support_service=support_service,
            registry=registry,
            approval_service=approval_service,
            audit_service=audit_service,
            action_service=action_service,
            policy_engine=policy_engine,
            agent_service=agent_service,
        )

    def _provider_for_case(
        self,
        case: SupportAgentEvaluationCase,
        mode: EvaluationMode,
        settings: Settings,
    ) -> LLMProvider:
        if mode == EvaluationMode.LIVE:
            return OllamaProvider(settings)
        fail_with = None
        if case.failure_injection:
            if case.failure_injection.type == FailureInjectionType.LLM_TIMEOUT:
                fail_with = "timeout"
            elif case.failure_injection.type == FailureInjectionType.LLM_UNAVAILABLE:
                fail_with = "unavailable"
        return ScriptedLLMProvider(case.scripted_decisions, fail_with=fail_with)

    def _apply_tool_faults(
        self,
        registry: ToolRegistry,
        failure: EvaluationFailureInjection | None,
    ) -> None:
        if failure is None or failure.tool_name is None or not registry.contains(failure.tool_name):
            return
        if failure.type == FailureInjectionType.TOOL_DOMAIN_ERROR:
            registry.register(FailingTool(registry.get(failure.tool_name)), allow_replace=True)
        if failure.type in {
            FailureInjectionType.TOOL_UNEXPECTED_EXCEPTION,
            FailureInjectionType.ACTION_EXECUTION_FAILURE,
        }:
            registry.register(
                FailingTool(registry.get(failure.tool_name), unexpected=True),
                allow_replace=True,
            )

    def _build_case_result(
        self,
        case: SupportAgentEvaluationCase,
        mode: EvaluationMode,
        model: str | None,
        agent_result,
        events: list[AuditEvent],
        env: EvaluationEnvironment,
        latency_ms: int,
        starting_ticket_count: int | None,
    ) -> AgentEvaluationCaseResult:
        actual_policy = self._policy_decision_from_events(events)
        executed_tools = [result.tool_name for result in agent_result.tool_results]
        if case.approval_decision is False:
            approval_status = ApprovalStatus.DENIED
        elif agent_result.approvals_required:
            approval_status = agent_result.approvals_required[0].status
        else:
            approval_status = self._latest_approval_status(env)
        failed_checks: list[str] = []
        parse_success = True
        failure_recovered = False
        if agent_result.error:
            parse_success = "json" not in agent_result.error.lower()
            failure_recovered = agent_result.status in {AgentStatus.FAILED, AgentStatus.ESCALATED}
        if case.failure_injection is not None:
            failure_recovered = agent_result.status == case.expected_status
        refund_total = None
        if case.expected_order_id:
            try:
                order = env.support_service.get_order(case.expected_order_id)
                refund_total = str(order.refund_total)
            except Exception:
                refund_total = None
        ticket_count = None
        if case.customer_id:
            ticket_count = len(env.support_service.get_customer_tickets(case.customer_id))
        ticket_count_delta = (
            ticket_count - starting_ticket_count
            if ticket_count is not None and starting_ticket_count is not None
            else None
        )
        return AgentEvaluationCaseResult(
            case_id=case.id,
            mode=mode,
            model=model or case.model,
            success=False,
            expected_status=case.expected_status,
            actual_status=agent_result.status,
            expected_tools=case.expected_tools,
            actual_tools=[call.tool_name for call in agent_result.tool_calls],
            executed_tools=executed_tools,
            expected_policy_decision=case.expected_policy_decision,
            actual_policy_decision=actual_policy,
            approval_status=approval_status,
            step_count=len(agent_result.decision_history),
            latency_ms=latency_ms,
            failure_recovered=failure_recovered,
            parse_success=parse_success,
            refund_total=refund_total,
            ticket_count=ticket_count,
            ticket_count_delta=ticket_count_delta,
            final_response=agent_result.response,
            error=agent_result.error,
            failed_checks=failed_checks,
        )

    def _policy_decision_from_events(self, events: list[AuditEvent]) -> PolicyDecision | None:
        for event in reversed(events):
            if event.event_type == AuditEventType.POLICY_CHECKED:
                decision = event.details.get("decision")
                if isinstance(decision, str):
                    return PolicyDecision(decision)
        return None

    def _latest_approval_status(self, env: EvaluationEnvironment) -> ApprovalStatus | None:
        approvals = env.approval_service.repository.list_pending()
        if approvals:
            return approvals[-1].status
        return None
