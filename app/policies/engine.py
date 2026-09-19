from datetime import UTC, datetime

from app.policies.models import PolicyDecision, PolicyDecisionResult, ProposedAction
from app.policies.rules import (
    CustomerOwnershipRule,
    OrderDeliveredRule,
    OrderExistsRule,
    PolicyContext,
    RefundAmountRule,
    RefundReasonRule,
    RemainingRefundableRule,
    ReturnWindowRule,
)
from app.support.service import SupportService


class PolicyEngine:
    def __init__(self, support_service: SupportService) -> None:
        self.support_service = support_service
        self.refund_rules = [
            OrderExistsRule(),
            CustomerOwnershipRule(),
            OrderDeliveredRule(),
            ReturnWindowRule(),
            RefundReasonRule(),
            RemainingRefundableRule(),
            RefundAmountRule(),
        ]

    def build_context(
        self,
        action: ProposedAction,
        customer_id: str | None = None,
        now: datetime | None = None,
    ) -> PolicyContext:
        order = None
        if "order_id" in action.arguments:
            try:
                order = self.support_service.get_order(str(action.arguments["order_id"]))
            except Exception:
                order = None
        return PolicyContext(
            customer_id=customer_id,
            order=order,
            refund_policy=self.support_service.get_refund_policy(),
            now=now or datetime.now(UTC),
            previous_refund_total=order.refund_total if order else 0,
        )

    def evaluate(
        self,
        action: ProposedAction,
        context: PolicyContext,
    ) -> PolicyDecisionResult:
        if action.tool_name == "reverse_refund":
            return PolicyDecisionResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reason="Refund reversals always require explicit approval.",
                policy_name="refund_reversal_policy_v1",
                action=action,
                rule_results=[],
            )
        if action.tool_name != "issue_refund":
            return PolicyDecisionResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reason="No auto-execution policy exists for this action.",
                policy_name="default_high_risk_policy_v1",
                action=action,
                rule_results=[],
            )

        results = [rule.evaluate(action, context) for rule in self.refund_rules]
        decisive_failures = [result for result in results if not result.passed and result.decision]
        if decisive_failures:
            decision = decisive_failures[0].decision or PolicyDecision.ESCALATE
            return PolicyDecisionResult(
                decision=decision,
                reason=decisive_failures[0].reason,
                policy_name="northstar_refund_policy_v1",
                action=action,
                rule_results=[result.model_dump(mode="json") for result in results],
            )

        amount_result = next(
            result for result in results if result.rule_name == "refund_amount_threshold"
        )
        decision = amount_result.decision or PolicyDecision.ESCALATE
        return PolicyDecisionResult(
            decision=decision,
            reason=amount_result.reason,
            policy_name="northstar_refund_policy_v1",
            action=action,
            rule_results=[result.model_dump(mode="json") for result in results],
        )
