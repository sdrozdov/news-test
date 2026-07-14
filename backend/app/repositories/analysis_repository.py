"""Data-access layer for articles and their analyses.

Repositories own SQLAlchemy queries and nothing else — no HTTP, no AI. They
``flush`` (to populate ids / enforce constraints) but never ``commit``; the
service owns the transaction boundary. Everything is scoped by ``user_id`` so a
user only ever reads or mutates their own rows. Article relationships are eagerly
loaded via ``selectinload`` to avoid async lazy-loading during serialization.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Analysis, Article, Sentiment
from app.schemas.analysis import ArticleInput


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_article_by_url(self, user_id: str, url: str) -> Article | None:
        result = await self._session.execute(
            select(Article).where(Article.user_id == user_id, Article.url == url)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _apply_fields(article: Article, data: ArticleInput) -> None:
        article.title = data.title
        article.description = data.description
        article.content = data.content
        article.image_url = data.image_url
        article.source_name = data.source_name
        article.published_at = data.published_at

    async def upsert_article(self, user_id: str, data: ArticleInput) -> Article:
        """Insert the article for a user, or refresh its fields if it exists.

        Resilient to a concurrent insert of the same (user, url): if the unique
        constraint fires on flush, we roll back, re-read the row the other request
        created, and fall through to the update path.
        """
        article = await self.get_article_by_url(user_id, data.url)
        if article is not None:
            self._apply_fields(article, data)
            await self._session.flush()
            return article

        article = Article(user_id=user_id, url=data.url)
        self._session.add(article)
        self._apply_fields(article, data)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            article = await self.get_article_by_url(user_id, data.url)
            if article is None:
                raise
            self._apply_fields(article, data)
            await self._session.flush()
        return article

    async def _get_analysis_by_article(self, article_id: UUID) -> Analysis | None:
        result = await self._session.execute(
            select(Analysis).where(Analysis.article_id == article_id)
        )
        return result.scalar_one_or_none()

    async def upsert_analysis(
        self,
        article_id: UUID,
        *,
        summary: str,
        sentiment: Sentiment,
        sentiment_score: float,
        model: str,
    ) -> tuple[Analysis, bool]:
        """Create or update the analysis for an article. Returns (analysis, created)."""
        analysis = await self._get_analysis_by_article(article_id)
        created = analysis is None
        if analysis is None:
            analysis = Analysis(article_id=article_id)
            self._session.add(analysis)
        analysis.summary = summary
        analysis.sentiment = sentiment
        analysis.sentiment_score = sentiment_score
        analysis.model = model
        await self._session.flush()
        return analysis, created

    async def get_analysis(self, user_id: str, analysis_id: UUID) -> Analysis | None:
        result = await self._session.execute(
            select(Analysis)
            .join(Article, Analysis.article_id == Article.id)
            .where(Analysis.id == analysis_id, Article.user_id == user_id)
            .options(selectinload(Analysis.article))
        )
        return result.scalar_one_or_none()

    async def list_analyses(
        self, user_id: str, *, limit: int = 50, offset: int = 0, query: str | None = None
    ) -> list[Analysis]:
        stmt = (
            select(Analysis)
            .join(Article, Analysis.article_id == Article.id)
            .where(Article.user_id == user_id)
        )
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Article.title.ilike(like),
                    Analysis.summary.ilike(like),
                    Article.source_name.ilike(like),
                )
            )
        stmt = (
            stmt.options(selectinload(Analysis.article))
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_analysis(self, user_id: str, analysis_id: UUID) -> bool:
        """Delete one of the user's results (its analysis and the owning article)."""
        analysis = await self.get_analysis(user_id, analysis_id)
        if analysis is None:
            return False
        article = analysis.article
        await self._session.delete(analysis)
        if article is not None:
            await self._session.delete(article)
        return True
