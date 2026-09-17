from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from app.core.config import Settings
from app.policies.models import ProposedAction
from app.tools.base import Tool
from app.tools.models import ToolRiskLevel


class SafetyAction(StrEnum):
    EXECUTE = "execute"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class SafetyDecision(BaseModel):
    action: SafetyAction
    reason: str
    requires_approval: bool = False
    proposed_action: ProposedAction | None = None


class AgentSafetyController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, tool: Tool, validated_arguments: dict[str, Any]) -> SafetyDecision:
        if tool.risk_level == ToolRiskLevel.READ_ONLY:
            return SafetyDecision(action=SafetyAction.EXECUTE, reason="Read-only tool is allowed.")
        if tool.risk_level == ToolRiskLevel.LOW_RISK_WRITE:
            if self.settings.agent_allow_low_risk_writes:
                return SafetyDecision(
                    action=SafetyAction.EXECUTE,
                    reason="Low-risk write is enabled for the synthetic Phase 3 demo.",
                )
            return SafetyDecision(
                action=SafetyAction.REQUIRE_APPROVAL,
                reason="Low-risk writes are disabled by configuration.",
                requires_approval=True,
                proposed_action=self._proposed_action(tool, validated_arguments),
            )
        return SafetyDecision(
            action=SafetyAction.REQUIRE_APPROVAL,
            reason="High-risk write tools are never auto-executed by the Phase 3 runtime.",
            requires_approval=True,
            proposed_action=self._proposed_action(tool, validated_arguments),
        )

    def _proposed_action(self, tool: Tool, arguments: dict[str, Any]) -> ProposedAction:
        estimated_value = None
        amount = arguments.get("amount")
        if amount is not None:
            estimated_value = Decimal(str(amount))
        rollback_tool = "reverse_refund" if tool.name == "issue_refund" else None
        return ProposedAction(
            action_type=tool.name,
            tool_name=tool.name,
            arguments=arguments,
            risk_level=tool.risk_level,
            reversible=tool.name == "issue_refund",
            rollback_tool=rollback_tool,
            rollback_arguments=None,
            estimated_value=estimated_value,
        )
