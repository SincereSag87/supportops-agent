from collections import Counter
from threading import Lock
from typing import Any


class MetricsStore:
    """Thread-safe in-process metrics for the local demo runtime."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()
        self._totals: Counter[str] = Counter()

    def increment(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[key] += amount

    def observe(self, key: str, value: float) -> None:
        with self._lock:
            self._counters[f"{key}.count"] += 1
            self._totals[f"{key}.total"] += value

    def count_model(self, model: str | None) -> None:
        self.increment(f"agent.model_usage.{model or 'default'}")

    def count_tool_usage(self, tool_name: str, *, success: bool | None = None) -> None:
        self.increment("tools.tool_calls")
        self.increment(f"tools.usage.{tool_name}")
        if success is True:
            self.increment("tools.tool_successes")
        elif success is False:
            self.increment("tools.tool_failures")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = Counter(self._counters)
            totals = Counter(self._totals)

        def average(key: str) -> float:
            count = counters.get(f"{key}.count", 0)
            total = totals.get(f"{key}.total", 0.0)
            return round(total / count, 2) if count else 0.0

        return {
            "requests": {
                "requests_total": counters["requests.total"],
                "requests_successful": counters["requests.successful"],
                "requests_failed": counters["requests.failed"],
                "average_request_latency_ms": average("requests.latency_ms"),
            },
            "agent": {
                "agent_requests": counters["agent.requests"],
                "completed": counters["agent.completed"],
                "awaiting_approval": counters["agent.awaiting_approval"],
                "escalated": counters["agent.escalated"],
                "failed": counters["agent.failed"],
                "average_agent_latency_ms": average("agent.latency_ms"),
                "average_steps": average("agent.steps"),
                "model_usage": _prefixed(counters, "agent.model_usage."),
                "structured_parse_failures": counters["agent.structured_parse_failures"],
                "repair_attempts": counters["agent.repair_attempts"],
                "repair_successes": counters["agent.repair_successes"],
            },
            "tools": {
                "tool_calls": counters["tools.tool_calls"],
                "tool_successes": counters["tools.tool_successes"],
                "tool_failures": counters["tools.tool_failures"],
                "usage_by_name": _prefixed(counters, "tools.usage."),
                "high_risk_proposals": counters["tools.high_risk_proposals"],
                "high_risk_executions": counters["tools.high_risk_executions"],
            },
            "policy": {
                "allow": counters["policy.allow"],
                "require_approval": counters["policy.require_approval"],
                "deny": counters["policy.deny"],
                "escalate": counters["policy.escalate"],
            },
            "approvals": {
                "approval_requests": counters["approvals.requests"],
                "approvals_granted": counters["approvals.granted"],
                "approvals_denied": counters["approvals.denied"],
                "approval_replay_blocks": counters["approvals.replay_blocks"],
            },
            "actions": {
                "refunds_executed": counters["actions.refunds_executed"],
                "reversals_executed": counters["actions.reversals_executed"],
                "action_failures": counters["actions.failures"],
            },
            "evaluation": {
                "evaluation_runs": counters["evaluation.runs"],
                "scripted_runs": counters["evaluation.scripted_runs"],
                "live_runs": counters["evaluation.live_runs"],
                "evaluation_failures": counters["evaluation.failures"],
            },
            "safety": {
                "unauthorized_action_blocks": counters["safety.unauthorized_action_blocks"],
                "loop_guard_triggers": counters["safety.loop_guard_triggers"],
                "max_step_escalations": counters["safety.max_step_escalations"],
                "audit_fail_closed_blocks": counters["safety.audit_fail_closed_blocks"],
            },
            "errors": _prefixed(counters, "errors."),
        }


def _prefixed(counters: Counter[str], prefix: str) -> dict[str, int]:
    return {
        key.removeprefix(prefix): value
        for key, value in sorted(counters.items())
        if key.startswith(prefix)
    }
