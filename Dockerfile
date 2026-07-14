# Single-image deploy: build the React frontend, then run the FastAPI backend
# which serves both the /api routes and the built frontend. One process, one
# port, one URL — no CORS, no separate frontend host. Build context = repo root.

# --- Stage 1: build the frontend ---
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# VITE_API_BASE_URL is left unset so the app calls same-origin /api.
RUN npm run build            # -> /web/dist

# --- Stage 2: Python backend that also serves the built frontend ---
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
# Drop the compiled SPA where main.py looks for it (backend/static).
COPY --from=web /web/dist ./backend/static

WORKDIR /app/backend

EXPOSE 8000
# Apply DB migrations, then serve. `alembic upgrade head` is a no-op when the DB
# is already at the latest revision.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
