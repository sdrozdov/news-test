"""Schemas for the analyze/store flow and the persisted result resource."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.article import Sentiment


def _require_http_url(value: str) -> str:
    candidate = value.strip()
    parsed = urlsplit(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("must be an http(s) URL")
    return candidate


class ArticleInput(BaseModel):
    """The article the user selected — the ``POST /api/analyses`` body.

    Constraints match the DB columns (so oversized input is a clean 422, not a
    500) and require real http(s) URLs (so nothing unsafe is stored or later
    rendered into an href/src).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=1024)
    description: str | None = Field(default=None, max_length=20_000)
    content: str | None = Field(default=None, max_length=20_000)
    url: str = Field(min_length=1, max_length=2048)
    image_url: str | None = Field(default=None, max_length=2048)
    source_name: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return _require_http_url(value)

    @field_validator("image_url")
    @classmethod
    def _validate_image_url(cls, value: str | None) -> str | None:
        return _require_http_url(value) if value else None


class AnalyzeRequest(BaseModel):
    article: ArticleInput


class AIResult(BaseModel):
    """Structured output returned by the AI client."""

    model_config = ConfigDict(str_strip_whitespace=True)

    summary: str = Field(min_length=1)
    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def _check_sign_consistency(self) -> AIResult:
        # Reject only a *gross* contradiction between the label and the score; a
        # mild disagreement (e.g. positive with -0.05) is common and still usable,
        # so it shouldn't fail the whole analysis.
        tolerance = 0.35
        if self.sentiment == Sentiment.positive and self.sentiment_score < -tolerance:
            raise ValueError("positive sentiment cannot have a strongly negative score")
        if self.sentiment == Sentiment.negative and self.sentiment_score > tolerance:
            raise ValueError("negative sentiment cannot have a strongly positive score")
        return self


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    title: str
    description: str | None = None
    image_url: str | None = None
    source_name: str | None = None
    published_at: datetime | None = None


class AnalysisRead(BaseModel):
    """A saved result: the AI analysis together with its article."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    summary: str
    sentiment: Sentiment
    sentiment_score: float
    model: str
    created_at: datetime
    updated_at: datetime
    article: ArticleRead
