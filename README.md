# SupportOps Agent

A local-first AI support operations agent focused on tool calling, policy enforcement, human approval, auditability, and safe automated actions.

## Overview

SupportOps Agent is an original portfolio and client-demo project for building an agentic support operations system from first principles. Phase 7 adds a polished Gradio Operations Console that consumes the FastAPI backend over HTTP while preserving the policy, approval, action, audit, and evaluation boundaries.

The LLM proposes actions. The runtime decides whether they may execute.

## Architecture

```mermaid
flowchart TD
    A[User] --> B[AgentRunner]
    B --> C[LLM Decision]
    C --> D[ProposedAction]
    D --> E[PolicyEngine]
    E --> F[ALLOW]
    E --> G[REQUIRE_APPROVAL]
    E --> H[DENY]
    E --> I[ESCALATE]
    F --> J[ActionService]
    G --> K[ApprovalService / Human]
    K --> J
    H --> L[Stop]
    I --> M[Human Escalation]
    J --> N[ToolRegistry]
    N --> O[Support Backend]
    P[AuditService] -. observes .- B
    P -. observes .- E
    P -. observes .- K
    P -. observes .- J
```

Phase 5 evaluation flow:

```mermaid
flowchart TD
    A[Benchmark Case] --> B[Fresh Agent Environment]
    B --> C[AgentRunner]
    C --> D[Tools / Policy / Approval / Audit]
    D --> E[Observed Final State]
    E --> F[Evaluator]
    F --> G[Tool Accuracy]
    F --> H[Policy Accuracy]
    F --> I[Approval Safety]
    F --> J[Action Safety]
    F --> K[Final State]
    F --> L[Audit Completeness]
    F --> M[Recovery]
    M --> N[Evaluation Report]
```

Phase 6 API architecture:

```mermaid
flowchart TD
    A[Client] -->|HTTP| B[FastAPI]
    B --> C[SupportService]
    B --> D[AgentService]
    D --> E[AgentRunner]
    E --> F[PolicyEngine]
    F --> G[ApprovalService]
    G --> H[ActionService]
    B --> I[AuditService]
    B --> J[EvaluationService]
    H --> K[Synthetic Backend]
    C --> K
    J --> K
```

Phase 7 UI architecture:

```mermaid
flowchart TD
    A[Browser] --> B[Gradio Operations Console]
    B -->|HTTP| C[FastAPI]
    C --> D[Support Data]
    C --> E[AgentService]
    C --> F[ApprovalService]
    C --> G[AuditService]
    C --> H[EvaluationService]
    H --> I[AgentRunner]
    E --> I
    I --> J[PolicyEngine]
    J --> K[ActionService]
    K --> L[Synthetic Backend]
    D --> L
```

## Gradio Operations Console

Start the backend in one terminal:

```bash
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Start the UI in another terminal:

```bash
uv run python -m ui.app
```

Open:

```text
http://127.0.0.1:7860
```

The UI talks to the API through `SupportOpsAPIClient`; it does not import or call support repositories, policy services, approval services, action services, or evaluation services directly.

## Client Demo Without Ollama

Scripted scenarios use the exact same runtime safety, policy, approval, action, and audit services as the live agent path, but with deterministic decision inputs. This lets clients inspect the system even when local model inference is unavailable.

When Ollama or a selected model is unavailable, the UI shows a friendly message and keeps scripted demos, approvals, audit, reset, and scripted evaluation available.

## Operations Console Tabs

| Tab | Purpose |
| --- | --- |
| Operations | Inspect synthetic customers, orders, tickets, and refund policy |
| Agent Request | Run live model requests or deterministic scripted demos |
| Approvals | Review, approve, or deny pending actions |
| Audit Trail | Inspect chronological request audit events |
| Evaluation | Run scripted or live benchmark evaluation |
| System | Check API/Ollama/state health and reset demo state |

The Agent Request tab displays status, response, request id, tool calls, tool results, approval requirements, safe execution trace, and an authorization panel. The trace is intentionally a safe execution trace, not chain-of-thought.

The Approvals tab calls the API approval endpoints. It never executes tools directly.

The System tab reset control requires explicit confirmation and affects synthetic demo data only.

## Client Demo Workflow

1. Open Operations and inspect `ORD-1001`.
2. Run the `order-status` scripted demo.
3. Run the `low-refund` scripted demo.
4. Reset state.
5. Run the `medium-refund` scripted demo.
6. Approve it as `demo-manager`.
7. Inspect `ORD-1002`.
8. Open Audit Trail.
9. Run the `high-refund` scripted demo.
10. Run scripted evaluation.

## FastAPI Backend

Run the API:

```bash
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

The API uses an application-scoped service container, so synthetic support state, pending approvals, and audit events survive across HTTP requests for the lifetime of the server. `POST /demo/reset` rebuilds that state for repeatable demos.

Live Ollama calls are currently blocking local calls. A live model request may occupy a worker until inference completes or times out.

## Why There Is No Direct Refund Endpoint

The API is only a transport layer. Sensitive actions remain behind:

Agent proposal -> PolicyEngine -> Approval if required -> ActionService -> Tool

There is no `POST /refund` route. Routes do not bypass policy decisions, approval verification, approval replay protection, or audit requirements.

## API Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Basic API status |
| `GET /health/ollama` | Local Ollama reachability and configured model |
| `GET /health/state` | Safe synthetic state counts |
| `GET /customers` | Synthetic customer summaries |
| `GET /customers/{customer_id}` | Customer detail with order/ticket ids |
| `GET /orders/{order_id}` | Order detail and refundable amount |
| `GET /customers/{customer_id}/orders` | Customer orders |
| `GET /tickets/{ticket_id}` | Ticket detail |
| `GET /customers/{customer_id}/tickets` | Customer tickets |
| `GET /policies/refund` | Current synthetic refund policy |
| `POST /agent/requests` | Live agent request through Ollama |
| `GET /approvals/pending` | Pending approval list |
| `POST /approvals/{approval_id}/approve` | Trusted approval and execution |
| `POST /approvals/{approval_id}/deny` | Trusted denial |
| `GET /audit/requests/{request_id}` | Chronological request audit |
| `GET /audit/recent` | Recent audit events |
| `GET /evaluation/benchmarks` | Registered benchmark metadata |
| `POST /evaluation/run` | Run scripted or live benchmark |
| `POST /demo/scenarios/{scenario_id}` | Deterministic scripted API scenario |
| `POST /demo/reset` | Demo-only state reset |

## Scripted Demo API

Scripted demo scenarios are deterministic and do not pretend to be live model inference. Supported IDs:

- `order-status`
- `low-refund`
- `medium-refund`
- `high-refund`
- `old-order`
- `ticket-create`

## API Error Handling

Errors use a consistent shape:

```json
{
  "error": {
    "code": "MODEL_NOT_AVAILABLE",
    "message": "The requested local model is not available."
  }
}
```

Domain not-found errors map to `404`, approval conflicts to `409`, unavailable local models to `503`, and malformed agent decisions to `502`. Stack traces are not returned.

## CORS

The API prepares for the Phase 7 Gradio console with:

```text
CORS_ORIGINS=http://localhost:7860,http://127.0.0.1:7860
```

It does not default to `*`.

## Why Agent Evaluation Differs From Chatbot Evaluation

A support operations agent is not successful because it writes convincing prose. It is successful only when the whole system behaves correctly:

- selects the right tools
- passes valid arguments
- applies policy using trusted data
- handles approval gates
- avoids unauthorized execution
- leaves the backend in the expected state
- records audit events
- fails safely when dependencies misbehave

## Why Final State Matters More Than Fluent Text

A support agent can produce a polished answer while executing the wrong action. Phase 5 evaluation therefore inspects backend state, approvals, policy results, executed tools, and audit events. Final response text is checked only with lightweight substring expectations.

## Evaluation Modes

`scripted` mode uses deterministic LLM decisions and is the primary correctness benchmark. It proves runtime logic, policy, approvals, execution safety, audit, and recovery without Ollama.

`live` mode uses Ollama and is supplemental. It measures local model structured-output reliability and behavior, but model availability does not affect deterministic benchmark correctness.

## Benchmark Scenarios

`benchmarks/support_agent_eval.json` contains normal support scenarios and injected failures:

- order status
- customer order list
- low-value refund auto-allow
- medium refund pending approval
- medium refund approved
- approval denied
- high-value refund escalation
- outside-window denial
- undelivered-order denial
- invalid-reason escalation
- support ticket creation
- unknown order
- malformed JSON repair
- malformed JSON failure
- LLM timeout
- unknown tool recovery
- duplicate call loop
- max-step exhaustion
- audit pre-write fail-closed behavior

Every benchmark case starts with fresh synthetic repositories, tool registry, approval service, audit service, policy engine, action service, and agent runner.

## Metrics

The evaluator reports separate metrics instead of one vague score:

- task success rate
- tool selection accuracy
- policy accuracy
- approval accuracy
- action safety accuracy
- final state accuracy
- escalation accuracy
- audit completeness
- failure recovery
- structured parse success
- average steps
- average latency

Tool selection distinguishes proposed tools from executed tools. Security-sensitive cases fail if forbidden tools execute.

## Why Prompt Instructions Are Not Authorization

Prompt instructions are useful guidance, but they are not a security boundary. Authorization comes from trusted application code:

- trusted support data loaded by repositories
- deterministic policy rules
- explicit approval records created by `ApprovalService`
- replay checks on consumed approvals
- audited execution through `ActionService`

The model cannot approve its own action, forge approval, skip audit logging, alter policy thresholds, or execute high-risk tools directly.

## Policy Engine

`PolicyEngine` evaluates `ProposedAction` objects against a trusted `PolicyContext`. The context uses application data, not model assertions:

- customer id
- trusted order record
- stored refund policy
- current time
- previous refund totals
- tool risk level

Refund rules are explicit:

- order must exist
- order must belong to the customer when customer context exists
- order must be delivered
- delivery must be inside the 30-day return window
- refund reason must be allowed
- refund amount must be greater than zero
- refund amount must not exceed remaining refundable amount

Refund amount outcomes:

| Amount | Decision |
| --- | --- |
| `<= 100.00` | `ALLOW` |
| `> 100.00` and `<= 500.00` | `REQUIRE_APPROVAL` |
| `> 500.00` | `ESCALATE` |

Invalid reasons escalate for human review. Undelivered or outside-window orders are denied.

## Approval Workflow

`ApprovalService` owns trusted approval decisions. Approval requests store the proposed action, policy decision, status, request id, and consumption metadata.

Approvals are replay-protected:

- denied approvals cannot execute
- nonexistent approvals cannot execute
- approvals for different actions cannot execute
- consumed approvals cannot execute again
- approval decisions are application-side records, not model-generated booleans

## ActionService

`ActionService` is the only Phase 4 path for executing policy-controlled high-risk actions. It verifies policy, approval requirements, tool arguments, and audit logging before and after execution.

Auto-execution is intentionally narrow. `issue_refund` may auto-execute only when policy returns `ALLOW`. `reverse_refund` always requires approval.

## Audit Trail

`AuditService` appends events through an in-memory repository. Normal APIs do not delete or mutate historical events.

Events include:

- request received
- model called
- tool selected
- policy checked
- approval requested
- approval granted or denied
- tool started
- tool completed or failed
- action executed
- approval consumed
- escalation
- request completion or failure

Audit details contain safe structured metadata such as ids, statuses, decisions, amounts, tool names, and policy outcomes. They do not store hidden chain-of-thought.

## Reversal Policy

Refund reversal uses `reverse_refund`, preserves original refund records, creates a reversal record, restores totals, and is always approval-required in Phase 4.

## Structured Output Hardening

The agent still requires JSON-only decisions. If the model returns malformed JSON, the runner makes at most one repair attempt using `AGENT_DECISION_REPAIR_ATTEMPTS=1`. If repair fails, the request fails safely.

Local LLM calls use `LLM_TIMEOUT_SECONDS=90` through the Ollama/OpenAI-compatible client to avoid indefinite hangs.

## Failure Recovery

Failure handling is deterministic and documented in `docs/failure-recovery.md`. Examples:

- malformed JSON gets one repair attempt
- LLM timeout fails safely with no write action
- unknown tools become safe observations
- duplicate tool loops escalate
- max-step exhaustion escalates
- approval denial and replay never execute
- high-risk actions fail closed if pre-execution audit logging fails

## Synthetic Dataset

All records are fictional Northstar Commerce data:

- `CUS-1001` Jordan Lee, `ORD-1001`, Wireless Headphones, `79.99 USD`
- `CUS-1002` Morgan Chen, `ORD-1002`, Laptop Docking Station, `299.99 USD`
- `ORD-1003`, high-value `749.99 USD` escalation case
- older delivered order outside the return window
- shipped but undelivered order

Emails use `example.test`.

## CLI

Run the agent:

```bash
uv run python -m app.main --agent "My headphones arrived damaged. Can I get a refund?" --customer-id CUS-1001 --show-trace
```

Approval commands:

```bash
uv run python -m app.main --pending-approvals
uv run python -m app.main --approve <approval-id> --actor "demo-manager"
uv run python -m app.main --deny <approval-id> --actor "demo-manager" --comment "Not approved."
uv run python -m app.main --audit-request <request-id>
```

Because normal storage is in-memory and resets per CLI process, Phase 4 includes a single-process demo flow:

```bash
uv run python -m app.main --demo-approval-flow
uv run python -m app.main --demo-approval-flow --approve-demo
```

The demo creates a medium-value approval request and, with `--approve-demo`, executes it once and proves replay is blocked.

Support backend commands:

```bash
uv run python -m app.main --list-tools
uv run python -m app.main --customer CUS-1001
uv run python -m app.main --order ORD-1001
uv run python -m app.main --refund-policy
```

Evaluation commands:

```bash
uv run python -m app.main --evaluate benchmarks/support_agent_eval.json
uv run python -m app.main --evaluate benchmarks/support_agent_eval.json --case low-value-refund
uv run python -m app.main --evaluate benchmarks/support_agent_eval.json --output json
uv run python -m app.main --evaluate benchmarks/support_agent_eval.json --save runtime/evaluations/support-agent.json
uv run python -m app.main --evaluate benchmarks/support_agent_eval.json --evaluation-mode live --model llama3.2
```

PowerShell API examples:

```powershell
$body = @{
    user_input = "What is the status of my order ORD-1001?"
    customer_id = "CUS-1001"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/agent/requests" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Medium refund approval demo:

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/demo/reset" `
    -Method Post `
    -ContentType "application/json" `
    -Body (@{ confirm = $true } | ConvertTo-Json)

$pending = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/demo/scenarios/medium-refund" `
    -Method Post

$approvalId = $pending.approvals_required[0].approval_id

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/approvals/$approvalId/approve" `
    -Method Post `
    -ContentType "application/json" `
    -Body (@{ actor = "demo-manager"; comment = "Approved for demo." } | ConvertTo-Json)
```

## Current Phase 7 Capabilities

- Centralized policy engine.
- Trusted refund policy context.
- Approval repository and service.
- Approval replay protection.
- Centralized action execution service.
- Append-only in-memory audit trail.
- AgentRunner integration for allow, approval, deny, and escalation outcomes.
- JSON repair attempt for malformed model decisions.
- LLM timeout configuration.
- Deterministic tests for policy, approvals, action execution, audit, and bypass protection.
- Pydantic benchmark schema.
- Scripted and live evaluation modes.
- Per-case result model and aggregate report.
- Deterministic metrics for tools, policy, approvals, action safety, final state, audit, recovery, parse success, steps, and latency.
- Failure injection for malformed output, provider failure, loops, max steps, tool errors, and audit failures.
- FastAPI application factory and app-scoped service container.
- HTTP endpoints for health, synthetic support data, agent requests, approvals, audit, evaluation, and scripted demos.
- Demo-only state reset for repeatable client testing.
- Gradio Operations Console backed by the FastAPI API.
- API client with friendly handling for offline backend, model unavailable, timeouts, approval conflicts, and malformed responses.
- UI tabs for operations, agent requests, approvals, audit, evaluation, and system health.
- Client-friendly scripted demo workflow that works without Ollama.

## Known Limitations

- In-memory state resets between ordinary CLI processes.
- No external database yet.
- No production authentication or authorization layer yet.
- Live local model structured-output quality may vary.
- API state is in-memory and resets when the server restarts.
- API authentication is intentionally deferred.
- UI is local-first and expects the FastAPI backend at `API_BASE_URL`.

## Quick Start

```bash
uv sync
uv run pytest
uv run ruff check .
uv run python -m app.main --evaluate benchmarks/support_agent_eval.json
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000
uv run python -m ui.app
uv run python -m app.main --demo-approval-flow --approve-demo
```

## Roadmap

1. Agent foundation & tool contracts [x]
2. Synthetic support backend [x]
3. Tool calling & agent decision loop [x]
4. Policy enforcement, approvals & audit trail [x]
5. Agent evaluation & failure recovery [x]
6. FastAPI backend [x]
7. Gradio operations console [x]
8. Observability, deployment & portfolio release

## Security / Privacy

All records are synthetic. No real customer data, payment card data, authentication secrets, payment processor integration, external support API, or production database is used.

Do not commit `.env`, `.venv/`, logs, model caches, runtime approval/audit state, secrets, or unrelated files.
