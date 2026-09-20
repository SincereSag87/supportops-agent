# Deployment Guide

SupportOps Agent v1.0.0 is optimized for local-first demos and private evaluation. It does not require Ollama for scripted demos.

## Option A: Local Client Demo

Best for recruiter demos, portfolio walkthroughs, and client discovery calls.

Terminal 1:

```bash
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
uv run python -m ui.app
```

Open:

```text
http://127.0.0.1:7860
```

Ollama is optional. Scripted scenarios and evaluation work without a live model.

## Option B: Private VM

Run FastAPI and Gradio on a private Linux VM. Optionally run Ollama on the same host if RAM/CPU/GPU resources are sufficient.

Consider:

- Firewall rules for ports 8000 and 7860 or a reverse proxy
- HTTPS termination
- Process manager such as systemd
- RAM and model storage for Ollama
- CPU/GPU availability
- Environment variables from `.env.example`
- Log file destination if `LOG_FILE` is set
- The current in-memory storage limitation

Productionizing this option would add authentication, RBAC, durable persistence, backup, monitoring, and secrets management.

## Option C: Split Model Host

FastAPI and Gradio can run separately from a private Ollama inference host.

Use this only over a trusted network. The model host should not be exposed publicly. Review firewall rules, TLS, request timeouts, and model resource capacity.

## Docker

Build:

```bash
docker build -t supportops-agent:1.0.0 .
```

Run API:

```bash
docker run --rm -p 8000:8000 supportops-agent:1.0.0
```

Run UI by overriding the command:

```bash
docker run --rm -p 7860:7860 -e API_BASE_URL=http://host.docker.internal:8000 supportops-agent:1.0.0 uv run python -m ui.app
```

Ollama is not packaged inside the application image. If live model requests are needed, run Ollama externally and set `OLLAMA_BASE_URL`.
