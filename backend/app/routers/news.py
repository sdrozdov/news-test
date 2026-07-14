"""Live news discovery — search and category top-headlines. Results are not
persisted here; the user analyzes a chosen article via POST /api/analyses.

Both routes require a signed-in user (so the shared GNews quota isn't burned by
anonymous callers)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.clients.reader_client import ArticleReader
from app.dependencies import get_current_user, get_news_service, get_reader
from app.schemas.common import UPSTREAM_RESPONSES
from app.schemas.news import ExtractedArticle, SearchResponse
from app.services.news_service import NewsService

router = APIRouter(prefix="/news", tags=["news"], dependencies=[Depends(get_current_user)])


@router.get("/search", response_model=SearchResponse, responses=UPSTREAM_RESPONSES)
async def search_news(
    q: str = Query(min_length=1, max_length=200, description="Search query"),
    lang: str | None = Query(default=None, min_length=2, max_length=5),
    max_results: int = Query(default=10, ge=1, le=25, alias="max"),
    page: int = Query(default=1, ge=1, le=10, description="Page (paid GNews plans)"),
    service: NewsService = Depends(get_news_service),
) -> SearchResponse:
    articles = await service.search(q, lang=lang, max_results=max_results, page=page)
    return SearchResponse(query=q, count=len(articles), articles=articles)


@router.get("/top-headlines", response_model=SearchResponse, responses=UPSTREAM_RESPONSES)
async def top_headlines(
    category: str = Query(default="general", description="News category for the briefing feed"),
    lang: str | None = Query(default=None, min_length=2, max_length=5),
    max_results: int = Query(default=10, ge=1, le=25, alias="max"),
    page: int = Query(default=1, ge=1, le=10, description="Page (paid GNews plans)"),
    service: NewsService = Depends(get_news_service),
) -> SearchResponse:
    articles = await service.top_headlines(category, lang=lang, max_results=max_results, page=page)
    return SearchResponse(query=category, count=len(articles), articles=articles)


@router.get("/extract", response_model=ExtractedArticle, responses=UPSTREAM_RESPONSES)
async def extract_article(
    url: str = Query(min_length=1, max_length=2048, description="Article URL to read"),
    reader: ArticleReader = Depends(get_reader),
) -> ExtractedArticle:
    """Reader-mode extraction of an article's main text for inline reading."""
    return await reader.extract(url)
