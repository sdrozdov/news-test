"""Schemas for live news search (the discovery step, not persisted directly)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """A normalized news article, shared by the search results and analyze input."""

    title: str
    description: str | None = None
    content: str | None = None
    url: str
    image_url: str | None = None
    source_name: str | None = None
    published_at: datetime | None = None


class SearchResponse(BaseModel):
    query: str
    count: int = Field(description="Number of articles returned")
    articles: list[NewsArticle]


class ArticleBlock(BaseModel):
    """One piece of extracted content — a paragraph or an inline image."""

    type: str = Field(description='"text" or "image"')
    value: str = Field(description="Paragraph text, or an image URL")


class ExtractedArticle(BaseModel):
    """Reader-mode content extracted from an article page for inline reading."""

    url: str
    title: str | None = None
    author: str | None = None
    image: str | None = None
    site_name: str | None = None
    blocks: list[ArticleBlock] = Field(description="Ordered text/image content blocks")
