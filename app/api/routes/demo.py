from fastapi import APIRouter, Depends

from app.agent.runner import AgentRunner
from app.agent.safety import AgentSafetyController
from app.api.dependencies import ServiceContainer, get_container
from app.api.errors import error_response
from app.api.models import DemoResetRequest, serialize_agent_result
from app.evaluation.models import decision_json
from app.evaluation.recovery import ScriptedLLMProvider
from app.services.agent_service import AgentService

router = APIRouter(prefix="/demo", tags=["demo"])
ContainerDep = Depends(get_container)


SCENARIOS: dict[str, dict[str, object]] = {
    "order-status": {
        "user_input": "What is the status of my order ORD-1001?",
        "customer_id": "CUS-1001",
        "decisions": [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Order status requires an order lookup.",
                tool_name="order_lookup",
                tool_arguments={"order_id": "ORD-1001"},
            ),
            decision_json(
                decision_type="final_response",
                reasoning_summary="The order lookup returned the status.",
                final_response="Order ORD-1001 is delivered.",
            ),
        ],
    },
    "low-refund": {
        "user_input": "My headphones arrived damaged. Can I get a refund for ORD-1001?",
        "customer_id": "CUS-1001",
        "decisions": [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="The low-value damaged order can be proposed for refund.",
                tool_name="issue_refund",
                tool_arguments={
                    "order_id": "ORD-1001",
                    "amount": "79.99",
                    "reason": "damaged",
                    "idempotency_key": "api-demo-low-refund",
                },
            ),
            decision_json(
                decision_type="final_response",
                reasoning_summary="The policy-approved refund succeeded.",
                final_response="The refund was completed for ORD-1001.",
            ),
        ],
    },
    "medium-refund": {
        "user_input": "Please refund my defective docking station ORD-1002.",
        "customer_id": "CUS-1002",
        "decisions": [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="The medium refund requires policy and approval handling.",
                tool_name="issue_refund",
                tool_arguments={
                    "order_id": "ORD-1002",
                    "amount": "299.99",
                    "reason": "defective",
                    "idempotency_key": "api-demo-medium-refund",
                },
            )
        ],
    },
    "high-refund": {
        "user_input": "Please refund high-value order ORD-1003.",
        "customer_id": "CUS-1003",
        "decisions": [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="The high-value refund must go through policy.",
                tool_name="issue_refund",
                tool_arguments={
                    "order_id": "ORD-1003",
                    "amount": "749.99",
                    "reason": "defective",
                    "idempotency_key": "api-demo-high-refund",
                },
            )
        ],
    },
    "old-order": {
        "user_input": "Please refund old order ORD-1004.",
        "customer_id": "CUS-1004",
        "decisions": [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="The old order refund must be checked against policy.",
                tool_name="issue_refund",
                tool_arguments={
                    "order_id": "ORD-1004",
                    "amount": "49.99",
                    "reason": "damaged",
                    "idempotency_key": "api-demo-old-order",
                },
            )
        ],
    },
    "ticket-create": {
        "user_input": "Please open a support ticket for my damaged headphones.",
        "customer_id": "CUS-1001",
        "decisions": [
            decision_json(
                decision_type="tool_call",
                reasoning_summary="Creating a support ticket is low risk.",
                tool_name="create_ticket",
                tool_arguments={
                    "customer_id": "CUS-1001",
                    "order_id": "ORD-1001",
                    "subject": "Damaged headphones",
                    "description": "Customer reports damaged headphones.",
                    "priority": "normal",
                },
            ),
            decision_json(
                decision_type="final_response",
                reasoning_summary="Ticket creation succeeded.",
                final_response="A support ticket was created.",
            ),
        ],
    },
}


@router.post("/scenarios/{scenario_id}")
def run_demo_scenario(
    scenario_id: str,
    container: ServiceContainer = ContainerDep,
):
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        return error_response(404, "SCENARIO_NOT_FOUND", "Unknown scripted demo scenario.")
    service = _scripted_agent_service(container, scenario["decisions"])
    result = service.handle_request(
        str(scenario["user_input"]),
        customer_id=str(scenario["customer_id"]),
        model="scripted-demo",
    )
    response = serialize_agent_result(result).model_dump(mode="json")
    response["mode"] = "scripted-demo"
    response["scenario_id"] = scenario_id
    return response


@router.post("/reset")
def reset_demo(
    request: DemoResetRequest,
    container: ServiceContainer = ContainerDep,
) -> dict[str, str]:
    if not request.confirm:
        return error_response(400, "RESET_CONFIRMATION_REQUIRED", "Set confirm=true.")
    container.reset_demo_state()
    return {"status": "reset", "mode": "demo-only"}


def _scripted_agent_service(container: ServiceContainer, decisions: object) -> AgentService:
    runner = AgentRunner(
        llm_provider=ScriptedLLMProvider(list(decisions)),
        tool_registry=container.tool_registry,
        safety_controller=AgentSafetyController(container.settings),
        settings=container.settings,
        policy_engine=container.policy_engine,
        action_service=container.action_service,
        audit_service=container.audit_service,
    )
    return AgentService(
        runner,
        approval_service=container.approval_service,
        action_service=container.action_service,
        audit_service=container.audit_service,
    )
