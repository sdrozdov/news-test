"""News provider client.

``NewsClient`` is a Protocol so the rest of the app depends on the capability,
not on GNews. Swapping providers (or faking it in tests) means implementing two
methods. ``GNewsClient`` adapts the GNews v4 ``/search`` and ``/top-headlines``
endpoints. Note: real pagination (``page`` > 1) requires a paid GNews plan; the
free tier returns the first page only.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Protocol

import httpx

from app.config import Settings
from app.errors import NewsAPIError
from app.schemas.news import NewsArticle

# Dedup key for headlines: lowercase, collapse anything non-alphanumeric. This
# makes the same story punctuation/spacing/source-suffix insensitive, so a wire
# story surfaced by several outlets (or re-served with a tweaked URL) counts once.
_TITLE_KEY_RE = re.compile(r"[^a-z0-9]+")


def title_dedup_key(title: str | None) -> str:
    return _TITLE_KEY_RE.sub(" ", (title or "").lower()).strip()

logger = logging.getLogger(__name__)

# GNews' supported top-headlines categories.
GNEWS_CATEGORIES = frozenset(
    {
        "general",
        "world",
        "nation",
        "business",
        "technology",
        "entertainment",
        "sports",
        "science",
        "health",
    }
)


class NewsClient(Protocol):
    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        max_results: int | None = None,
        page: int = 1,
    ) -> list[NewsArticle]: ...

    async def top_headlines(
        self,
        category: str,
        *,
        lang: str | None = None,
        max_results: int | None = None,
        page: int = 1,
    ) -> list[NewsArticle]: ...


class GNewsClient:
    """Adapter for https://gnews.io (free tier: 100 requests/day, 10 per request)."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._http = http_client or httpx.AsyncClient(timeout=15.0)

    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        max_results: int | None = None,
        page: int = 1,
    ) -> list[NewsArticle]:
        return await self._fetch(
            "/search",
            {
                "q": query,
                "lang": lang or self._settings.news_default_lang,
                "max": max_results or self._settings.news_default_max,
                "page": page,
            },
        )

    async def top_headlines(
        self,
        category: str,
        *,
        lang: str | None = None,
        max_results: int | None = None,
        page: int = 1,
    ) -> list[NewsArticle]:
        cat = category if category in GNEWS_CATEGORIES else "general"
        return await self._fetch(
            "/top-headlines",
            {
                "category": cat,
                "lang": lang or self._settings.news_default_lang,
                "max": max_results or self._settings.news_default_max,
                "page": page,
            },
        )

    async def _fetch(self, path: str, params: dict) -> list[NewsArticle]:
        if not self._settings.gnews_api_key:
            raise NewsAPIError("News is not configured (set GNEWS_API_KEY).", status_code=503)

        params = {**params, "apikey": self._settings.gnews_api_key}
        url = f"{self._settings.gnews_base_url}{path}"

        try:
            response = await self._http.get(url, params=params)
        except httpx.HTTPError:
            logger.exception("GNews request failed")
            raise NewsAPIError("Could not reach the news provider.") from None

        if response.status_code == 429:
            raise NewsAPIError(
                "News API rate limit reached (free tier is 100/day). Try again later.",
                status_code=429,
            )
        if response.status_code in (401, 403):
            raise NewsAPIError(
                "News API rejected the request — check GNEWS_API_KEY.", status_code=502
            )
        if response.status_code >= 400:
            raise NewsAPIError(f"News API error (HTTP {response.status_code}).")

        payload = response.json()
        articles = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for item in payload.get("articles", []):
            url_value = item.get("url")
            # url is required (it's the uniqueness key downstream). Also drop
            # duplicates the provider sometimes returns — the same url, or the
            # same story surfaced twice — so the feed never shows a repeat.
            if not url_value or url_value in seen_urls:
                continue
            title_key = title_dedup_key(item.get("title"))
            if title_key and title_key in seen_titles:
                continue
            seen_urls.add(url_value)
            if title_key:
                seen_titles.add(title_key)
            articles.append(self._to_article(item))
        return articles

    @staticmethod
    def _to_article(raw: dict) -> NewsArticle:
        published_at = _parse_datetime(raw.get("publishedAt"))
        source = raw.get("source") or {}
        return NewsArticle(
            title=raw.get("title") or "(untitled)",
            description=raw.get("description"),
            content=raw.get("content"),
            url=raw["url"],
            image_url=raw.get("image"),
            source_name=source.get("name"),
            published_at=published_at,
        )

    async def aclose(self) -> None:
        await self._http.aclose()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
