# Security Review

SupportOps Agent v1.0.0 is a portfolio and client-demo system. It is designed to show safety architecture for agentic support operations, not to process real customer data.

## Trust Boundaries

| Component | Trust Level | Responsibility |
| --- | --- | --- |
| Model | Untrusted proposer | Suggests one structured decision at a time |
| PolicyEngine | Trusted authorization logic | Evaluates actions using application data |
| ApprovalService | Trusted human decision boundary | Records explicit approve/deny decisions |
| ActionService | Trusted execution boundary | Verifies policy and approval before tool execution |
| AuditService | Operational evidence | Records append-only safe audit events |
| FastAPI | Transport only | Calls application services; does not bypass authorization |
| Gradio | API client only | Talks to FastAPI over HTTP; does not call services directly |

## Tool Security

- Tools expose explicit Pydantic input schemas.
- Tool arguments are validated before execution.
- Tools declare risk levels: `READ_ONLY`, `LOW_RISK_WRITE`, or `HIGH_RISK_WRITE`.
- Unknown tools are rejected.
- There is no arbitrary function execution.
- There is no direct refund API endpoint.
- The LLM cannot approve its own actions.
- High-risk actions remain behind policy, approval when required, ActionService, and audit.

## Financial Action Safety

- Money uses `Decimal`, not float.
- Refund tools validate positive amount and remaining refundable balance.
- Refunds require idempotency keys.
- Reversals preserve history instead of deleting records.
- Approval replay is blocked after one execution.
- Refund thresholds come from trusted application policy data.
- The model cannot change refund limits or claim policy facts as trusted truth.

## Known Security Limitations

Not included in v1.0.0:

- Authentication
- RBAC
- Multi-tenancy
- Encrypted database
- External secrets manager
- Persistent production database
- Production payment gateway
- Malware scanning
- Distributed rate limiting
- Enterprise identity provider
- Real customer PII handling

The project uses synthetic records only and should not be connected to real payment or support systems without adding production controls.
