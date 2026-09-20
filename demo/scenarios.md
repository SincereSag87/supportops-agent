# Demo Scenarios

## 1. Order Status

Customer: Jordan Lee, `CUS-1001`

Order: `ORD-1001`

Request:

```text
What is the status of my order ORD-1001?
```

Expected outcome: completed read-only answer showing delivered status.

Demonstrates: tool-backed answers instead of invented order facts.

## 2. Low Refund

Customer: Jordan Lee, `CUS-1001`

Order: `ORD-1001`

Amount: `79.99`

Request:

```text
My headphones arrived damaged. Can I get a refund?
```

Expected policy: `ALLOW`

Expected outcome: automatic policy-controlled synthetic refund.

Demonstrates: trusted policy context and safe action execution.

## 3. Medium Refund

Customer: Morgan Chen, `CUS-1002`

Order: `ORD-1002`

Amount: `299.99`

Request:

```text
Please refund my defective docking station ORD-1002.
```

Expected policy: `REQUIRE_APPROVAL`

Expected outcome: approval request is created; refund executes only after trusted approval.

Demonstrates: human-in-the-loop and approval replay protection.

## 4. High Refund

Order: `ORD-1003`

Amount: `749.99`

Expected policy: `ESCALATE`

Expected outcome: no refund execution.

Demonstrates: high-value escalation.

## 5. Old Order

Order: `ORD-1004`

Expected policy: `DENY`

Expected outcome: no refund execution because the order is outside the return window.

Demonstrates: deterministic policy denial.

## 6. Ticket Create

Customer: Jordan Lee, `CUS-1001`

Request:

```text
Please open a support ticket for my damaged headphones.
```

Expected outcome: low-risk support ticket creation.

Demonstrates: controlled low-risk write behavior.
