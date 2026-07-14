.PHONY: help install backend frontend test lint db-up db-down

help:
	@echo "Targets:"
	@echo "  install    Install backend (venv) and frontend deps"
	@echo "  db-up      Start local Postgres (docker compose)"
	@echo "  db-down    Stop local Postgres"
	@echo "  backend    Run the API at http://localhost:8000"
	@echo "  frontend   Run the web app at http://localhost:5173"
	@echo "  test       Run backend tests"
	@echo "  lint       Ruff (backend) + tsc (frontend)"

install:
	python3.11 -m venv .venv
	.venv/bin/pip install -r backend/requirements-dev.txt
	cd frontend && npm install

db-up:
	docker compose up -d

db-down:
	docker compose down

backend:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && ../.venv/bin/python -m pytest -q

lint:
	cd backend && ../.venv/bin/ruff check .
	cd frontend && npm run typecheck
