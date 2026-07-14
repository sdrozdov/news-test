"""Application factory and ASGI entrypoint.

``create_app`` is the composition root: it builds the engine + clients from
settings, attaches them to ``app.state``, wires CORS, error handlers, and the
``/api`` router. Tests call it with test settings; production imports ``app``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.clients.ai_client import OpenAIClient
from app.clients.auth_client import WorkOSAuth
from app.clients.news_client import GNewsClient
from app.clients.reader_client import ArticleReader
from app.config import Settings, get_settings
from app.db.session import create_engine_and_factory, init_models
from app.errors import register_exception_handlers
from app.routers import analyses, auth, health, news


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine, session_factory = create_engine_and_factory(settings)
    news_client = GNewsClient(settings)
    ai_client = OpenAIClient(settings)
    auth_client = WorkOSAuth(settings)
    reader_client = ArticleReader(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.auto_create_tables:
            await init_models(engine)
        yield
        await news_client.aclose()
        await reader_client.aclose()
        await ai_client.aclose()
        await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        summary="Search news, analyze with AI (summary + sentiment), and store results.",
        lifespan=lifespan,
    )

    # Shared singletons for dependency providers.
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.news_client = news_client
    app.state.ai_client = ai_client
    app.state.auth = auth_client
    app.state.reader = reader_client

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # The WorkOS session cookie is sent cross-origin in a split deploy, so
        # credentials must be allowed. Origins are an explicit list (never "*").
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router)
    api_router.include_router(auth.router)
    api_router.include_router(news.router)
    api_router.include_router(analyses.router)
    app.include_router(api_router)

    # Serve the built frontend (copied to backend/static in the Docker image) so
    # the whole app is one same-origin service. Absent in local dev (use the Vite
    # dev server), so the mount is guarded on the directory existing.
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()
