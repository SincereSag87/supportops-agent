# Changelog

## v1.0.0 - 2026-09-20

SupportOps Agent v1.0.0 is the polished portfolio and client-demo release.

### Added

- Local-first Ollama LLM provider abstraction with structured decision parsing, repair attempts, and timeouts.
- Synthetic Northstar Commerce support backend with customers, orders, tickets, refunds, and refund policy data.
- Tool contracts, schemas, risk levels, registry, idempotent refund behavior, and refund reversal foundation.
- AgentRunner with explicit state, safe decision traces, loop protection, max-step guard, and tool observation feedback.
- Central PolicyEngine with trusted policy context, refund thresholds, approval requirements, denial, and escalation.
- Human approval workflow with replay protection and trusted approval decisions.
- ActionService execution boundary with fail-closed audit behavior.
- Append-only audit events for requests, policies, approvals, actions, escalations, and failures.
- Deterministic 19-case evaluation benchmark for policy, approval, action safety, final state, audit, and recovery.
- FastAPI backend with synthetic data, agent, approvals, audit, evaluation, scripted demo, reset, health, and metrics endpoints.
- Gradio Operations Console for client-friendly demos over HTTP.
- Structured JSON logging, `X-Request-ID` middleware, in-process metrics, Docker packaging, CI, deployment docs, security docs, client handoff docs, and portfolio material.

### Safety Highlights

- The model proposes actions; the runtime authorizes them.
- Prompt instructions are not treated as an authorization boundary.
- High-impact actions are controlled by policy, approval, ActionService, and audit.
- Approval replay, approval mismatch, policy denial, and escalation cannot execute sensitive actions.
- Scripted demos exercise the same runtime safety services without requiring a live local model.
