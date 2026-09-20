# Synthetic Demo Package

This folder contains fully synthetic demo material for Northstar Commerce. No real customer, order, ticket, payment, or support data is included.

Use these scenarios for client calls, recruiter demos, or manual release checks.

Start the API:

```bash
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Start the UI:

```bash
uv run python -m ui.app
```

Open:

```text
http://127.0.0.1:7860
```

Scripted scenarios exercise the same policy, approval, action, audit, and evaluation services as the live path without requiring Ollama.
