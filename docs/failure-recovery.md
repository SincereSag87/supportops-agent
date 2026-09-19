# Failure Recovery

| Failure | Expected behavior | Recovery | Safety guarantee |
| --- | --- | --- | --- |
| Malformed decision | Attempt one JSON repair | Continue only if repaired | No guessed tool calls |
| LLM timeout | Fail safely | Return failed result | No write action |
| Unavailable model | Fail safely | Report provider error | No write action |
| Read-tool failure | Feed safe observation back to agent | Agent may respond or escalate | No crash or fabricated result |
| Write-tool failure | Return failed action result | Surface failure | No false success |
| Policy denial | Stop action | Return blocked result | Denied action is not executed |
| Approval denial | Stop action | Return deterministic denial response | Denied approval cannot execute |
| Approval replay | Reject execution | Raise replay error | One approval authorizes one execution only |
| Loop detection | Escalate | Stop repeated identical calls | No infinite tool loop |
| Max steps | Escalate | Stop after configured limit | No unbounded agent run |
| Pre-execution audit failure | Fail closed | Do not execute sensitive action | High-risk tool does not run without audit start |
| Post-execution audit failure | Surface serious failure | Do not hide the failure | Operator sees that audit completion failed |
