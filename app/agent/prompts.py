import json

from app.agent.context import AgentContext
from app.llm.models import ChatMessage, ChatRole

SYSTEM_PROMPT = """You are SupportOps Agent for fictional Northstar Commerce.

You must use available tools instead of inventing customer, order, ticket, refund, or policy facts.
Never fabricate tool results. Never claim an action happened unless a tool result confirms it.
Perform one action or decision at a time. Use read tools to gather required context.
Avoid duplicate unnecessary tool calls. Escalate when important information is missing.
Do not assume policies; inspect refund policy before proposing refund action.

Runtime safety rules:
- HIGH_RISK_WRITE tools require approval.
- You may propose HIGH_RISK_WRITE tools, but the runtime will stop before execution.
- READ_ONLY tools may execute automatically.
- LOW_RISK_WRITE tools may execute only when runtime configuration allows.

Return structured JSON only. Use a short decision rationale, not private step-by-step reasoning.
Never output private internal chain-of-thought.
"""


def build_agent_messages(context: AgentContext) -> list[ChatMessage]:
    user_payload = {
        "request": context.request.model_dump(mode="json"),
        "status": context.status,
        "step_count": context.step_count,
        "recent_messages": context.recent_messages,
        "tool_calls": context.tool_calls,
        "tool_results": context.tool_results,
        "available_tools": context.available_tools,
        "decision_formats": {
            "tool_call": {
                "decision_type": "tool_call",
                "reasoning_summary": "Short safe rationale.",
                "tool_name": "tool_name",
                "tool_arguments": {},
            },
            "final_response": {
                "decision_type": "final_response",
                "reasoning_summary": "Short safe rationale.",
                "final_response": "Customer-facing response.",
            },
            "escalate": {
                "decision_type": "escalate",
                "reasoning_summary": "Short safe rationale.",
                "escalation_reason": "Reason escalation is needed.",
            },
            "fail": {
                "decision_type": "fail",
                "reasoning_summary": "Short safe rationale.",
                "final_response": "Safe failure response.",
            },
        },
    }
    return [
        ChatMessage(role=ChatRole.SYSTEM, content=SYSTEM_PROMPT),
        ChatMessage(role=ChatRole.USER, content=json.dumps(user_payload, indent=2)),
    ]
