from functools import partial

import gradio as gr

from app.core.config import get_settings
from ui.api_client import SupportOpsAPIClient
from ui.callbacks import (
    approve_selected,
    deny_selected,
    load_audit,
    load_customer,
    load_customers,
    load_order,
    load_policy,
    load_ticket,
    recent_audit,
    refresh_approvals,
    refresh_system,
    reset_demo,
    run_evaluation,
    run_live_agent,
    run_scripted_demo,
)
from ui.components import (
    APPROVAL_COLUMNS,
    AUDIT_COLUMNS,
    CUSTOMER_COLUMNS,
    DEMO_SCENARIOS,
    FAILED_CASE_COLUMNS,
    TOOL_CALL_COLUMNS,
    TOOL_RESULT_COLUMNS,
    TRACE_COLUMNS,
)


def build_client() -> SupportOpsAPIClient:
    settings = get_settings()
    return SupportOpsAPIClient(
        base_url=settings.api_base_url,
        timeout=settings.api_timeout_seconds,
        agent_timeout=settings.agent_timeout_seconds,
        evaluation_timeout=settings.evaluation_timeout_seconds,
    )


def build_app(client: SupportOpsAPIClient | None = None) -> gr.Blocks:
    api = client or build_client()
    with gr.Blocks(title="SupportOps Agent") as app:
        gr.Markdown(
            """
# SupportOps Agent
Safe AI support operations with policy enforcement, human approval, auditability,
and deterministic evaluation.

Inspect synthetic support data, run agent workflows, review approvals, verify
audit trails, and test safety behavior.
"""
        )
        with gr.Accordion("Recommended Demo", open=False):
            gr.Markdown(
                """
1. Open Operations and inspect ORD-1001.
2. Run order-status scripted demo.
3. Run low-refund demo.
4. Reset state.
5. Run medium-refund demo.
6. Approve it as demo-manager.
7. Inspect ORD-1002.
8. Open Audit Trail.
9. Run high-refund demo.
10. Run scripted evaluation.
"""
            )

        with gr.Tab("Operations"):
            gr.Markdown("Inspect the fictional Northstar Commerce support state.")
            load_customers_btn = gr.Button("Load Customers")
            customers_grid = gr.Dataframe(headers=CUSTOMER_COLUMNS, label="Customers")
            customers_status = gr.Markdown()

            with gr.Row():
                customer_id = gr.Textbox(value="CUS-1001", label="Customer ID")
                load_customer_btn = gr.Button("Load Customer")
            customer_output = gr.Textbox(label="Customer", lines=8)

            with gr.Row():
                order_id = gr.Textbox(value="ORD-1001", label="Order ID")
                load_order_btn = gr.Button("Load Order")
            order_output = gr.Textbox(label="Order", lines=10)

            with gr.Row():
                ticket_id = gr.Textbox(value="TIC-1001", label="Ticket ID")
                load_ticket_btn = gr.Button("Load Ticket")
            ticket_output = gr.Textbox(label="Ticket", lines=8)

            load_policy_btn = gr.Button("Load Refund Policy")
            policy_output = gr.Textbox(label="Refund Policy", lines=9)

        with gr.Tab("Agent Request"):
            gr.Markdown(
                """
Live agent requests use the configured local Ollama model. If the model is
unavailable, scripted demos remain fully usable.
"""
            )
            with gr.Row():
                agent_customer = gr.Textbox(value="CUS-1001", label="Customer ID")
                agent_model = gr.Dropdown(["llama3.2", "gemma3"], value="llama3.2", label="Model")
            agent_input = gr.Textbox(
                value="What is the status of my order ORD-1001?",
                label="User request",
                lines=3,
            )
            run_live_btn = gr.Button("Run Live Agent")

            gr.Markdown("Deterministic demo - no live LLM used.")
            scenario = gr.Dropdown(
                DEMO_SCENARIOS,
                value="order-status",
                label="Scripted Demo Scenario",
            )
            run_demo_btn = gr.Button("Run Scripted Demo")

            agent_result = gr.Textbox(label="Result", lines=8)
            authorization = gr.Textbox(label="Policy / Authorization", lines=5)
            request_id_state = gr.Textbox(label="Request ID")
            tool_calls = gr.Dataframe(headers=TOOL_CALL_COLUMNS, label="Tool Calls")
            tool_results = gr.Dataframe(headers=TOOL_RESULT_COLUMNS, label="Tool Results")
            approval_requirements = gr.Dataframe(
                headers=APPROVAL_COLUMNS,
                label="Approval Requirements",
            )
            trace = gr.Dataframe(headers=TRACE_COLUMNS, label="Safe Execution Trace")

        with gr.Tab("Approvals"):
            gr.Markdown(
                "Approval decisions are trusted application-side actions. "
                "The UI never executes support tools directly."
            )
            refresh_approvals_btn = gr.Button("Refresh")
            approvals_status = gr.Markdown()
            approvals_grid = gr.Dataframe(headers=APPROVAL_COLUMNS, label="Pending Approvals")
            selected_approval = gr.Textbox(label="Selected Approval ID")
            actor = gr.Textbox(value="demo-manager", label="Actor")
            comment = gr.Textbox(label="Comment")
            with gr.Row():
                approve_btn = gr.Button("Approve Selected")
                deny_btn = gr.Button("Deny Selected")
            approval_result = gr.Textbox(label="Decision Result", lines=6)

        with gr.Tab("Audit Trail"):
            gr.Markdown(
                "The audit trail records operational decisions and execution events. "
                "It does not store private model chain-of-thought."
            )
            audit_request = gr.Textbox(label="Request ID")
            load_audit_btn = gr.Button("Load Audit")
            recent_limit = gr.Slider(1, 100, value=50, step=1, label="Recent limit")
            recent_audit_btn = gr.Button("Recent Audit")
            audit_status = gr.Markdown()
            audit_grid = gr.Dataframe(headers=AUDIT_COLUMNS, label="Audit Events")

        with gr.Tab("Evaluation"):
            gr.Markdown(
                """
Scripted evaluation proves runtime safety and workflow correctness
independently of local LLM quality.

Live evaluation measures model structured-decision reliability separately.
"""
            )
            with gr.Row():
                benchmark = gr.Dropdown(
                    ["support-agent-demo"],
                    value="support-agent-demo",
                    label="Benchmark",
                )
                eval_mode = gr.Dropdown(["scripted", "live"], value="scripted", label="Mode")
                eval_model = gr.Dropdown(["llama3.2", "gemma3"], value="llama3.2", label="Model")
            case_filter = gr.Textbox(label="Optional case filter")
            run_eval_btn = gr.Button("Run Evaluation")
            eval_summary = gr.Textbox(label="Aggregate Metrics", lines=14)
            failed_cases = gr.Dataframe(headers=FAILED_CASE_COLUMNS, label="Failed Cases")

        with gr.Tab("System"):
            gr.Markdown("System health and demo-only reset controls.")
            refresh_system_btn = gr.Button("Refresh")
            system_output = gr.Textbox(label="System", lines=12)
            reset_confirm = gr.Checkbox(label="I understand this resets all synthetic demo state.")
            reset_btn = gr.Button("Reset Demo")
            reset_output = gr.Markdown("This affects synthetic demo data only.")

        load_customers_btn.click(
            partial(load_customers, api),
            outputs=[customers_status, customers_grid],
        )
        load_customer_btn.click(
            partial(load_customer, api),
            inputs=customer_id,
            outputs=customer_output,
        )
        load_order_btn.click(partial(load_order, api), inputs=order_id, outputs=order_output)
        load_ticket_btn.click(partial(load_ticket, api), inputs=ticket_id, outputs=ticket_output)
        load_policy_btn.click(partial(load_policy, api), outputs=policy_output)

        live_outputs = [
            agent_result,
            authorization,
            tool_calls,
            tool_results,
            approval_requirements,
            trace,
            request_id_state,
        ]
        run_live_btn.click(
            partial(run_live_agent, api),
            inputs=[agent_input, agent_customer, agent_model],
            outputs=live_outputs,
        )
        run_demo_btn.click(partial(run_scripted_demo, api), inputs=scenario, outputs=live_outputs)

        refresh_approvals_btn.click(
            partial(refresh_approvals, api),
            outputs=[approvals_status, approvals_grid],
        )
        approve_btn.click(
            partial(approve_selected, api),
            inputs=[selected_approval, actor, comment],
            outputs=[approval_result, approvals_grid],
        )
        deny_btn.click(
            partial(deny_selected, api),
            inputs=[selected_approval, actor, comment],
            outputs=[approval_result, approvals_grid],
        )

        load_audit_btn.click(
            partial(load_audit, api),
            inputs=audit_request,
            outputs=[audit_status, audit_grid],
        )
        recent_audit_btn.click(
            partial(recent_audit, api),
            inputs=recent_limit,
            outputs=[audit_status, audit_grid],
        )

        run_eval_btn.click(
            partial(run_evaluation, api),
            inputs=[benchmark, eval_mode, eval_model, case_filter],
            outputs=[eval_summary, failed_cases],
        )
        refresh_system_btn.click(partial(refresh_system, api), outputs=system_output)
        reset_btn.click(partial(reset_demo, api), inputs=reset_confirm, outputs=reset_output)

    return app


def main() -> None:
    settings = get_settings()
    build_app().launch(server_name=settings.gradio_host, server_port=settings.gradio_port)


if __name__ == "__main__":
    main()
