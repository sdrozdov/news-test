"""Search + category orchestration — thin today, but the seam where ranking,
caching, or provider fan-out would live tomorrow."""

from __future__ import annotations

from app.clients.news_client import NewsClient
from app.schemas.news import NewsArticle


class NewsService:
    def __init__(self, news_client: NewsClient) -> None:
        self._news = news_client

    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        max_results: int | None = None,
        page: int = 1,
    ) -> list[NewsArticle]:
        cleaned = query.strip()
        if not cleaned:
            # A whitespace-only query passes the router's min_length; treat it as
            # an empty feed rather than forwarding "" and getting a provider 400.
            return []
        return await self._news.search(
            cleaned, lang=lang, max_results=max_results, page=page
        )

    async def top_headlines(
        self,
        category: str,
        *,
        lang: str | None = None,
        max_results: int | None = None,
        page: int = 1,
    ) -> list[NewsArticle]:
        return await self._news.top_headlines(
            category, lang=lang, max_results=max_results, page=page
        )
