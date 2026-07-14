"""Test fixtures: an app wired to in-memory SQLite with fake external clients.

No network and no Postgres required — the fakes stand in for GNews and OpenAI,
and SQLite exercises the real ORM + repository + service + router stack.
"""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.clients.ai_client import AIClient
from app.clients.news_client import NewsClient
from app.config import Settings
from app.db.base import Base
from app.dependencies import get_ai_client, get_news_client, get_reader
from app.main import create_app
from app.models.article import Sentiment
from app.schemas.analysis import AIResult
from app.schemas.news import NewsArticle

SAMPLE_ARTICLES = [
    NewsArticle(
        title="Renewable energy adoption hits record high",
        description="Solar and wind capacity grew sharply this year.",
        content="Global renewable capacity additions set a new record...",
        url="https://example.com/renewables",
        image_url="https://example.com/img/renewables.jpg",
        source_name="Example News",
    ),
    NewsArticle(
        title="Markets tumble amid uncertainty",
        description="Stocks fell as investors weighed new data.",
        content="Major indices dropped on Tuesday...",
        url="https://example.com/markets",
        source_name="Example Wire",
    ),
]


class FakeNewsClient:
    def __init__(self, articles: list[NewsArticle] | None = None) -> None:
        self._articles = articles if articles is not None else SAMPLE_ARTICLES

    async def search(self, query, *, lang=None, max_results=None, page=1) -> list[NewsArticle]:
        if page > 1:
            return []
        limit = max_results or len(self._articles)
        return self._articles[:limit]

    async def top_headlines(
        self, category, *, lang=None, max_results=None, page=1
    ) -> list[NewsArticle]:
        if page > 1:
            return []
        limit = max_results or len(self._articles)
        return self._articles[:limit]


class FakeAIClient:
    model = "fake-model"

    async def analyze(self, article: NewsArticle) -> AIResult:
        text = f"{article.title} {article.description or ''}".lower()
        negative = "tumble" in text or "fell" in text
        return AIResult(
            summary=f"Summary of '{article.title}'.",
            sentiment=Sentiment.negative if negative else Sentiment.positive,
            sentiment_score=-0.6 if negative else 0.7,
        )


class FakeReader:
    async def extract(self, url: str) -> dict:
        return {
            "url": url,
            "title": "Extracted title",
            "author": None,
            "image": None,
            "site_name": "Example",
            "blocks": [
                {"type": "text", "value": "First paragraph."},
                {"type": "image", "value": "https://example.com/pic.jpg"},
                {"type": "text", "value": "Second paragraph."},
            ],
        }


@pytest_asyncio.fixture
async def app():
    settings = Settings(
        _env_file=None,  # hermetic: never read the developer's real .env
        database_url="sqlite+aiosqlite://",
        auto_create_tables=False,  # created explicitly below
        openai_api_key="test",
        gnews_api_key="test",
        cors_origins="http://localhost",
    )
    application = create_app(settings)

    # Create schema on the app's (in-memory) engine.
    async with application.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fake_news: NewsClient = FakeNewsClient()
    fake_ai: AIClient = FakeAIClient()
    application.dependency_overrides[get_news_client] = lambda: fake_news
    application.dependency_overrides[get_ai_client] = lambda: fake_ai
    application.dependency_overrides[get_reader] = lambda: FakeReader()

    yield application

    await application.state.engine.dispose()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
