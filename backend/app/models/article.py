"""ORM models: an :class:`Article` and its 1:1 AI :class:`Analysis`.

The pair models one "result" shown to the user. An article is unique by URL, so
re-analyzing the same article updates the existing record instead of duplicating.
Types are kept portable (no Postgres-only columns) so the same models run on
SQLite in tests.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Sentiment(enum.StrEnum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class Article(Base):
    __tablename__ = "articles"
    # An article is unique per user (each user keeps their own copy + analysis),
    # so the same URL can be analyzed independently by different accounts.
    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_articles_user_url"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # WorkOS user id (or the local dev user) that owns this article.
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    url: Mapped[str] = mapped_column(String(2048), index=True)
    title: Mapped[str] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    image_url: Mapped[str | None] = mapped_column(String(2048), default=None)
    source_name: Mapped[str | None] = mapped_column(String(255), default=None)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    analysis: Mapped[Analysis | None] = relationship(
        back_populates="article",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), unique=True, index=True
    )
    summary: Mapped[str] = mapped_column(Text)
    sentiment: Mapped[Sentiment] = mapped_column(Enum(Sentiment, name="sentiment"))
    # Continuous polarity in [-1, 1]; the discrete label is stored alongside.
    sentiment_score: Mapped[float] = mapped_column(Float)
    model: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    article: Mapped[Article] = relationship(back_populates="analysis")
