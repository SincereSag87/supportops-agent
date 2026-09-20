CUSTOMER_COLUMNS = ["Customer ID", "Name", "Email", "Status"]
APPROVAL_COLUMNS = [
    "Approval ID",
    "Request ID",
    "Tool",
    "Action",
    "Amount",
    "Policy Reason",
    "Status",
    "Requested At",
]
TOOL_CALL_COLUMNS = ["Tool", "Arguments", "Call ID"]
TOOL_RESULT_COLUMNS = ["Tool", "Success", "Error", "Reversible", "Metadata"]
TRACE_COLUMNS = ["Step", "Decision", "Safe rationale", "Tool"]
AUDIT_COLUMNS = ["Timestamp", "Event", "Actor", "Tool", "Success", "Details"]
FAILED_CASE_COLUMNS = [
    "Case",
    "Expected Status",
    "Actual Status",
    "Failed Checks",
    "Tools",
    "Policy",
    "Approval",
    "Final State",
    "Error",
]
DEMO_SCENARIOS = [
    "order-status",
    "low-refund",
    "medium-refund",
    "high-refund",
    "old-order",
    "ticket-create",
]
DEMO_DESCRIPTIONS = {
    "order-status": "Read-only workflow.",
    "low-refund": "Policy-approved automatic refund.",
    "medium-refund": "Requires human approval.",
    "high-refund": "Escalates.",
    "old-order": "Denied by return-window policy.",
    "ticket-create": "Low-risk write.",
}
