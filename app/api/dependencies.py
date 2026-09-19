from dataclasses import dataclass
from functools import lru_cache

from app.agent.runner import AgentRunner
from app.agent.safety import AgentSafetyController
from app.approvals.repository import InMemoryApprovalRepository
from app.approvals.service import ApprovalService
from app.audit.repository import InMemoryAuditRepository
from app.audit.service import AuditService
from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.policies.engine import PolicyEngine
from app.services.action_service import ActionService
from app.services.agent_service import AgentService
from app.services.evaluation_service import EvaluationService
from app.services.health_service import HealthService
from app.support.service import SupportService, create_demo_support_service
from app.tools.registry import ToolRegistry
from app.tools.support_registry import create_support_tool_registry


@dataclass
class ServiceContainer:
    settings: Settings
    support_service: SupportService
    tool_registry: ToolRegistry
    approval_service: ApprovalService
    audit_service: AuditService
    policy_engine: PolicyEngine
    action_service: ActionService
    llm_provider: LLMProvider
    agent_service: AgentService
    evaluation_service: EvaluationService
    health_service: HealthService

    @classmethod
    def create(cls, settings: Settings | None = None) -> "ServiceContainer":
        resolved = settings or get_settings()
        support_service = create_demo_support_service()
        tool_registry = create_support_tool_registry(support_service)
        approval_service = ApprovalService(InMemoryApprovalRepository())
        audit_service = AuditService(InMemoryAuditRepository())
        policy_engine = PolicyEngine(support_service)
        action_service = ActionService(tool_registry, approval_service, audit_service)
        llm_provider = OllamaProvider(resolved)
        runner = AgentRunner(
            llm_provider=llm_provider,
            tool_registry=tool_registry,
            safety_controller=AgentSafetyController(resolved),
            settings=resolved,
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
        return cls(
            settings=resolved,
            support_service=support_service,
            tool_registry=tool_registry,
            approval_service=approval_service,
            audit_service=audit_service,
            policy_engine=policy_engine,
            action_service=action_service,
            llm_provider=llm_provider,
            agent_service=agent_service,
            evaluation_service=EvaluationService(resolved),
            health_service=HealthService(resolved, tool_registry),
        )

    def reset_demo_state(self) -> None:
        fresh = ServiceContainer.create(self.settings)
        self.support_service = fresh.support_service
        self.tool_registry = fresh.tool_registry
        self.approval_service = fresh.approval_service
        self.audit_service = fresh.audit_service
        self.policy_engine = fresh.policy_engine
        self.action_service = fresh.action_service
        self.llm_provider = fresh.llm_provider
        self.agent_service = fresh.agent_service
        self.evaluation_service = fresh.evaluation_service
        self.health_service = fresh.health_service


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    return ServiceContainer.create()
