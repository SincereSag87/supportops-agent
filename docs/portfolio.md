# Portfolio Notes

## One-Sentence Description

Built a local-first agentic support operations platform with structured tool calling, deterministic policy enforcement, human approval, audit trails, failure recovery, observability, and deterministic agent safety evaluation.

## Resume Bullets

- Built a Python 3.12 AI support operations platform using FastAPI, Gradio, Pydantic, Ollama-compatible local models, and deterministic synthetic support data.
- Implemented runtime safety controls where the LLM proposes actions but PolicyEngine, ApprovalService, ActionService, and audit requirements authorize execution.
- Designed a 19-case deterministic benchmark covering tool selection, policy decisions, approvals, action safety, final backend state, audit completeness, and failure recovery.
- Added approval replay protection, idempotent refunds, reversible-action foundations, structured logging, request tracing, metrics, CI, Docker packaging, and client handoff documentation.

## 30-Second Interview Explanation

SupportOps Agent is a local-first AI support operations demo. The important design choice is that the model never directly executes sensitive actions. It proposes structured tool decisions, and the runtime validates arguments, checks trusted policy data, requires approval when needed, executes through ActionService, and records an audit trail. I also built deterministic evaluation so safety is measured by backend state and authorization behavior, not just fluent text.

## 2-Minute Interview Explanation

I built SupportOps Agent to explore agentic support automation without hiding the hard parts behind an orchestration framework. The system has synthetic customers, orders, tickets, refunds, and refund policy data. The agent can inspect tool schemas, ask a local Ollama-compatible model for structured JSON decisions, execute safe read tools, and propose write actions.

The central safety boundary is application-side authorization. Refunds are evaluated by PolicyEngine using trusted order and policy data. Low-value eligible refunds can execute automatically. Medium-value refunds create ApprovalRequests and pause until a trusted human decision arrives. High-value or uncertain cases escalate. Approval replay is blocked, and ActionService is the only path for approved high-risk execution.

I added FastAPI, Gradio, audit trails, failure recovery, structured logging, request IDs, metrics, Docker packaging, CI, and a deterministic benchmark. The benchmark checks final backend state, policy decisions, approval behavior, audit completeness, and action safety, so the system does not get credit for a convincing answer when the actual state is wrong.

## Common Interview Questions

### Why not let the LLM execute tools directly?

Because prompt instructions are not authorization. The runtime validates and authorizes every action.

### Why build without LangGraph?

To understand and demonstrate the mechanics: state, tool selection, validation, policy, approval, action execution, audit, and recovery.

### How are refunds authorized?

PolicyEngine evaluates trusted order/policy facts. ApprovalService records human decisions. ActionService verifies policy and approval before execution.

### Why is prompt engineering insufficient for safety?

Models can produce incorrect or malicious-looking outputs. Security boundaries must live in deterministic application code.

### How do approvals prevent replay?

Approvals are consumed after one execution and cannot authorize another action.

### How do you evaluate agent safety?

The benchmark checks executed tools, policy decisions, approval status, final order state, audit events, and failure recovery.

### What happens if audit logging fails?

For high-risk pre-execution audit failure, ActionService fails closed and does not execute.

### How would you persist state in production?

Replace in-memory repositories with a database, add migrations, transaction boundaries, audit retention, backups, and idempotency constraints.

### How would you add RBAC?

Add authentication, roles, approval permissions, route authorization, and audit actor identity.

### How would you integrate Zendesk/Shopify/Stripe?

Wrap each external API as explicit tools with typed schemas, risk levels, idempotency, sandbox tests, policy rules, and audit events.
