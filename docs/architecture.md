# Architecture Decisions

## 1. Build The Tool Loop Without LangGraph First

Reason: understand execution boundaries and agent mechanics directly.

Benefit: the project owns tool validation, safety gates, state transitions, and audit events.

Tradeoff: more custom orchestration code.

## 2. Model Proposes, Runtime Authorizes

Reason: prompt instructions are not a security boundary.

Benefit: a model can suggest `issue_refund`, but policy, approval, ActionService, and audit decide whether it executes.

Tradeoff: more application code is required around the model.

## 3. Trusted Policy Context

Reason: the model must not be trusted to assert order values, delivery state, or refund limits.

Benefit: PolicyEngine evaluates against repository-backed data.

Tradeoff: policy requires explicit context-building.

## 4. Explicit Human Approval

Reason: high-impact actions need trusted user authorization.

Benefit: approvals are application records, not model-generated booleans.

Tradeoff: workflows can pause before execution.

## 5. Approval Replay Protection

Reason: one approval should authorize exactly one execution.

Benefit: replay attempts are blocked and visible.

Tradeoff: approval lifecycle must be tracked carefully.

## 6. Append-Only Audit Model

Reason: support operations need traceability.

Benefit: major transitions are recorded without hidden chain-of-thought.

Tradeoff: persistent audit storage is future work.

## 7. Deterministic Evaluation

Reason: agent safety should be testable independently from model quality.

Benefit: scripted benchmark proves policy, approval, action safety, final state, audit, and recovery.

Tradeoff: live model behavior is measured separately.

## 8. Scripted Client Demos

Reason: local Ollama models may be unavailable during a client call.

Benefit: the product remains demonstrable using the same runtime safety services.

Tradeoff: scripted demos are not live model inference.

## 9. FastAPI / Gradio Separation

Reason: the UI must not bypass backend authorization.

Benefit: Gradio is only an HTTP client; FastAPI owns service access.

Tradeoff: two local processes are needed for the full demo.
