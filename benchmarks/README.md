# SupportOps Agent Benchmarks

`support_agent_eval.json` is a fully synthetic benchmark for deterministic system evaluation.

The scripted mode evaluates the runtime, tools, policy engine, approval workflow, action safety, audit trail, and failure recovery without requiring Ollama.

Live mode uses the same case schema but relies on a local Ollama model, so model availability and structured-output reliability are reported separately from deterministic correctness.
