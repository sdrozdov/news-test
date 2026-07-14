"""Analysis orchestration: run the AI, persist the result, own the transaction.

The AI call happens *before* any write, so a failed analysis never leaves a
half-saved article behind; only successful results are stored. Everything is
scoped to a ``user_id`` so results never leak across accounts.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_client import AIClient
from app.errors import NotFoundError
from app.models.article import Analysis
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import ArticleInput


class AnalysisService:
    def __init__(self, session: AsyncSession, ai_client: AIClient) -> None:
        self._session = session
        self._repo = AnalysisRepository(session)
        self._ai = ai_client

    async def analyze_and_store(
        self, user_id: str, article_in: ArticleInput
    ) -> tuple[Analysis, bool]:
        """Analyze and persist for a user. Returns (analysis, created)."""
        # 1) Analyze first — if this fails, nothing is written.
        ai_result = await self._ai.analyze(article_in)

        # 2) Upsert the article and its analysis (1:1, idempotent per user+URL).
        article = await self._repo.upsert_article(user_id, article_in)
        analysis, created = await self._repo.upsert_analysis(
            article.id,
            summary=ai_result.summary,
            sentiment=ai_result.sentiment,
            sentiment_score=ai_result.sentiment_score,
            model=self._ai.model,
        )
        await self._session.commit()

        # `article` is still populated (expire_on_commit=False); attach it so
        # serialization needs no extra query.
        analysis.article = article
        return analysis, created

    async def list_results(
        self, user_id: str, *, limit: int, offset: int, query: str | None = None
    ) -> list[Analysis]:
        return await self._repo.list_analyses(user_id, limit=limit, offset=offset, query=query)

    async def get_result(self, user_id: str, analysis_id: UUID) -> Analysis:
        analysis = await self._repo.get_analysis(user_id, analysis_id)
        if analysis is None:
            raise NotFoundError("Result not found.")
        return analysis

    async def delete_result(self, user_id: str, analysis_id: UUID) -> None:
        deleted = await self._repo.delete_analysis(user_id, analysis_id)
        if not deleted:
            raise NotFoundError("Result not found.")
        await self._session.commit()
