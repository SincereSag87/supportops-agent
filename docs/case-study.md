# Case Study: Safe Refund Automation

## Problem

An AI support agent may need to perform real operational actions, but unrestricted autonomy is unsafe. A convincing model response is not enough. The system must prove that actions were authorized, executed correctly, and audited.

## Design

SupportOps Agent uses:

1. LLM proposal
2. Tool argument validation
3. Trusted policy context
4. PolicyEngine
5. ApprovalService when required
6. ActionService execution
7. Append-only audit events

## Medium Refund Flow

Request:

```text
Please refund my defective docking station ORD-1002.
```

Flow:

```text
request
-> proposed issue_refund
-> trusted order and refund policy lookup
-> PolicyEngine returns REQUIRE_APPROVAL
-> ApprovalRequest created
-> demo-manager approves
-> ActionService executes issue_refund
-> approval consumed
-> audit trail records the sequence
```

The original order is unchanged until approval is granted. A second attempt to reuse the approval is rejected.

## High-Value Flow

Order:

```text
ORD-1003, 749.99 USD
```

Policy result:

```text
ESCALATE
```

No refund executes. The result is visible in the agent response, audit trail, and evaluation benchmark.

## Lessons

- The model can suggest the next action, but it should not authorize the action.
- Trusted application data matters more than model assertions.
- Approval records need replay protection.
- Audit logging is part of safe execution, not an afterthought.
- Evaluation should inspect backend state, not only final prose.
