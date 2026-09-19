from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel

from app.domain.orders import Order, OrderStatus
from app.domain.policies import RefundPolicy
from app.policies.models import PolicyDecision, ProposedAction


class PolicyContext(BaseModel):
    customer_id: str | None = None
    order: Order | None = None
    refund_policy: RefundPolicy | None = None
    now: datetime = datetime.now(UTC)
    previous_refund_total: Decimal = Decimal("0.00")


class RuleResult(BaseModel):
    rule_name: str
    passed: bool
    decision: PolicyDecision | None = None
    reason: str


class PolicyRule(Protocol):
    name: str

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        """Evaluate one deterministic policy rule."""


class OrderExistsRule:
    name = "order_exists"

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        if context.order is None:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.DENY,
                reason="Order does not exist.",
            )
        return RuleResult(rule_name=self.name, passed=True, reason="Order exists.")


class CustomerOwnershipRule:
    name = "customer_ownership"

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        if context.order is None or context.customer_id is None:
            return RuleResult(
                rule_name=self.name,
                passed=True,
                reason="No customer context required.",
            )
        if context.order.customer_id != context.customer_id:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.DENY,
                reason="Order does not belong to the customer.",
            )
        return RuleResult(rule_name=self.name, passed=True, reason="Order belongs to customer.")


class OrderDeliveredRule:
    name = "order_delivered"

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        if context.order is None:
            return RuleResult(rule_name=self.name, passed=True, reason="Order checked elsewhere.")
        if context.order.status not in {
            OrderStatus.DELIVERED,
            OrderStatus.PARTIALLY_REFUNDED,
        }:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.DENY,
                reason="Order has not been delivered.",
            )
        return RuleResult(rule_name=self.name, passed=True, reason="Order is delivered.")


class ReturnWindowRule:
    name = "return_window"

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        if (
            context.order is None
            or context.refund_policy is None
            or context.order.delivered_at is None
        ):
            return RuleResult(
                rule_name=self.name,
                passed=True,
                reason="Return window not applicable.",
            )
        age_days = (context.now.date() - context.order.delivered_at.date()).days
        if age_days > context.refund_policy.return_window_days:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.DENY,
                reason="Order is outside the return window.",
            )
        return RuleResult(rule_name=self.name, passed=True, reason="Order is inside return window.")


class RefundReasonRule:
    name = "refund_reason"

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        if context.refund_policy is None:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.ESCALATE,
                reason="Refund policy is unavailable.",
            )
        reason = str(action.arguments.get("reason", ""))
        if reason not in context.refund_policy.allowed_reasons:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.ESCALATE,
                reason="Refund reason is not listed in allowed reasons.",
            )
        return RuleResult(rule_name=self.name, passed=True, reason="Refund reason is allowed.")


class RemainingRefundableRule:
    name = "remaining_refundable"

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        if context.order is None:
            return RuleResult(rule_name=self.name, passed=True, reason="Order checked elsewhere.")
        amount = Decimal(str(action.arguments.get("amount", "0")))
        if amount <= Decimal("0"):
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.DENY,
                reason="Refund amount must be greater than zero.",
            )
        if amount > context.order.remaining_refundable_amount:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.DENY,
                reason="Refund amount exceeds remaining refundable amount.",
            )
        return RuleResult(
            rule_name=self.name,
            passed=True,
            reason="Refund amount is within remaining refundable amount.",
        )


class RefundAmountRule:
    name = "refund_amount_threshold"

    def evaluate(self, action: ProposedAction, context: PolicyContext) -> RuleResult:
        if context.refund_policy is None:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                decision=PolicyDecision.ESCALATE,
                reason="Refund policy is unavailable.",
            )
        amount = Decimal(str(action.arguments.get("amount", "0")))
        if amount <= context.refund_policy.auto_refund_limit:
            return RuleResult(
                rule_name=self.name,
                passed=True,
                decision=PolicyDecision.ALLOW,
                reason="Refund amount is within automatic threshold.",
            )
        if amount <= context.refund_policy.approval_refund_limit:
            return RuleResult(
                rule_name=self.name,
                passed=True,
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reason="Refund amount requires human approval.",
            )
        return RuleResult(
            rule_name=self.name,
            passed=False,
            decision=PolicyDecision.ESCALATE,
            reason="Refund amount exceeds approval threshold.",
        )
