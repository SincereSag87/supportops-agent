# Client Demo Handoff

SupportOps Agent demonstrates safe AI support operations using fully synthetic Northstar Commerce data.

## What It Does

- Reads synthetic customer, order, ticket, refund, and policy data.
- Lets an LLM or scripted decision provider propose support actions.
- Validates tool arguments and risk levels.
- Authorizes sensitive actions through trusted policy logic.
- Requires human approval when policy demands it.
- Records audit events for operational evidence.
- Evaluates safety and workflow correctness with deterministic benchmarks.

## What Is Synthetic

All names, emails, orders, tickets, policies, and refunds are fictional. Email addresses use `example.test`. There is no payment processor and no real customer data.

## Recommended Demo Flow

1. Start FastAPI and Gradio.
2. Open Operations and inspect `ORD-1001`.
3. Run the `order-status` scripted demo.
4. Run the `low-refund` scripted demo.
5. Reset demo state.
6. Run the `medium-refund` scripted demo.
7. Approve as `demo-manager`.
8. Inspect `ORD-1002` and the audit trail.
9. Reset state.
10. Run the `high-refund` scripted demo.
11. Run the scripted benchmark.

## How Safe Automation Works

The model proposes an action. The runtime authorizes it using trusted application data, policy rules, approval records, ActionService checks, and audit requirements.

Low-value eligible refunds may execute automatically because the policy returns `ALLOW`. Medium-value refunds require human approval. High-value refunds escalate.

## Questions for a Client Pilot

- Which actions can AI perform automatically?
- Which actions require approval?
- What monetary thresholds apply?
- Which systems would tools connect to?
- What actions must never be automated?
- Which roles may approve actions?
- What audit retention is required?
- How should failed actions be recovered?
- What escalation SLA is required?
- Which customer data may the model see?
- What evaluation threshold is required before launch?

## Customization Paths

- Ecommerce returns
- SaaS support
- Billing workflows
- Account operations
- Ticket routing
- Knowledge lookup
- Back-office workflow assistance

The goal is not to replace support teams. The goal is controlled automation with explicit boundaries.
