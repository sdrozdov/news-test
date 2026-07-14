# News AI

## What it is

Search news, analyze a chosen article with AI (summary + sentiment), store it,
and browse your history. Sign-in scopes data per user.

## Run locally

Prereqs: Python 3.11+, Node 18+, Docker, an OpenAI key, a GNews key (free at gnews.io).

```bash
docker compose up -d                                   # Postgres
python3.11 -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
cp backend/.env.example backend/.env                   # add OPENAI_API_KEY + GNEWS_API_KEY
cd backend && ../.venv/bin/alembic upgrade head        # schema
../.venv/bin/uvicorn app.main:app --reload --port 8000 # API → :8000 (docs at /docs)

cd frontend && npm install && npm run dev              # app → :5173 (proxies /api → :8000)
```

WorkOS is optional locally — leave `WORKOS_*` unset to run in dev mode (single user, no login).

## Architecture

Layered backend, each layer depending only on the one below; external services
sit behind Protocols (swappable, faked in tests).

`routers → services → repositories → models` · `clients/` (GNews, OpenAI, WorkOS,
reader) · `schemas/` (Pydantic) · `config.py`, `errors.py`, `dependencies.py` (DI).

One Docker image builds the React app; FastAPI serves it alongside `/api`.
