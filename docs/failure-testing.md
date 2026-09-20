# Failure Testing

The system is designed to fail safely. Scripted evaluation and API demos make failure behavior testable without relying on live Ollama models.

| Failure | Trigger | Expected Behavior | User-Visible Result | Safety Guarantee | Recovery |
| --- | --- | --- | --- | --- | --- |
| Ollama unavailable | Stop Ollama or point `OLLAMA_BASE_URL` to an unavailable service | LLM provider maps connection failure to domain error | API returns clean 503; UI suggests scripted demos | No tool execution | Start Ollama or use scripted demos |
| Requested model unavailable | Request a missing model | Provider returns model-not-available error | Friendly model unavailable message | No action is executed | Install model or choose available one |
| Malformed LLM JSON | Script invalid response | One repair attempt | Repaired decision or safe failure | No guessed tool calls | Improve prompt/model or use scripted path |
| Repair fails | Return invalid JSON twice | Agent fails safely | Structured failure response | No write action | Inspect model output reliability |
| LLM timeout | Provider timeout | Agent fails/escalates safely | Timeout/unavailable message | No write action | Increase timeout or use smaller model |
| Unknown tool | Model selects missing tool | Tool result observation records failure | Agent can recover or fail safely | No arbitrary execution | Use registered tools only |
| Invalid tool arguments | Missing/wrong schema fields | Validation error observation | Agent can correct or fail | No malformed execution | Fix structured decision |
| Read-tool failure | Repository/domain error | Failure observation or escalation | Clear not-found/failure result | No write action | Human review or corrected request |
| Write-tool failure | Tool returns failure | ActionService does not claim success | Failed/escalated result | No false success | Retry with valid state |
| Duplicate loop | Same tool/args repeated too often | Loop guard escalates | Escalation response | Prevents infinite execution | Human review |
| Max-step exhaustion | Agent reaches step limit | Escalates | Max-step message | Stops runaway loop | Improve prompt/tool plan |
| Policy deny | Old/undelivered/ineligible refund | Policy returns DENY | Action blocked | No execution after denial | Human review if needed |
| Policy escalation | High value or invalid reason | Policy returns ESCALATE | Escalation response | No execution | Human support workflow |
| Approval denied | Trusted user denies | ApprovalService records denial | No execution | Denial cannot execute later | New request required |
| Approval replay | Reuse consumed approval | 409 conflict | Friendly replay rejection | No second execution | Create new request |
| Approval mismatch | Approval for different action | ActionService rejects | Conflict response | Prevents action substitution | Review approval details |
| Audit pre-execution failure | Audit repository failure before sensitive tool | ActionService fails closed | Execution refused | High-risk action not executed | Restore audit service |
| API unavailable from Gradio | Stop FastAPI | UI catches connection error | "SupportOps API is unavailable" | UI cannot bypass backend | Start API |
| Evaluation failure | Case assertion fails | Case recorded; run continues | Failed-case table | Failure is visible | Inspect failed checks |

## Intentional Release Failure Checks

The release validation intentionally exercises:

- Missing live model path, which returns a clean 503 without stack trace.
- Approval replay, which returns 409 and leaves the order refund total unchanged.
- Normal scripted demos after failures, proving recovery and state reset still work.
