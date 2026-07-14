"""FastAPI dependency providers — the composition root wiring layers together.

Clients live on ``app.state`` (built once in the app factory); services are
constructed per request around the request-scoped DB session. ``get_current_user``
resolves the signed-in user from the sealed-session cookie, or a fixed local user
when WorkOS isn't configured (dev mode). Tests override the providers with fakes.
"""

from __future__ import annotations

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_client import AIClient
from app.clients.auth_client import WorkOSAuth
from app.clients.news_client import NewsClient
from app.clients.reader_client import ArticleReader
from app.config import Settings
from app.db.session import get_session
from app.errors import UnauthorizedError
from app.schemas.user import UserRead
from app.services.analysis_service import AnalysisService
from app.services.news_service import NewsService

# Name of the sealed-session cookie set by WorkOS AuthKit.
COOKIE_NAME = "wos_session"

# Identity used when WorkOS isn't configured, so the app is fully usable locally
# (and in tests) without auth. All data is then owned by this single dev user.
DEV_USER = UserRead(id="local-dev-user", email="dev@localhost", first_name="Dev")


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_news_client(request: Request) -> NewsClient:
    return request.app.state.news_client


def get_ai_client(request: Request) -> AIClient:
    return request.app.state.ai_client


def get_auth(request: Request) -> WorkOSAuth:
    return request.app.state.auth


def get_reader(request: Request) -> ArticleReader:
    return request.app.state.reader


def get_news_service(news_client: NewsClient = Depends(get_news_client)) -> NewsService:
    return NewsService(news_client)


def get_analysis_service(
    session: AsyncSession = Depends(get_session),
    ai_client: AIClient = Depends(get_ai_client),
) -> AnalysisService:
    return AnalysisService(session, ai_client)


def set_session_cookie(response: Response, sealed: str, settings: Settings) -> None:
    """Single owner of the sealed-session cookie's name and security attributes."""
    response.set_cookie(
        COOKIE_NAME,
        sealed,
        max_age=settings.session_cookie_max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


async def get_current_user(
    request: Request,
    response: Response,
    auth: WorkOSAuth = Depends(get_auth),
    settings: Settings = Depends(get_settings_dep),
) -> UserRead:
    """Resolve the signed-in user from the sealed-session cookie.

    When WorkOS isn't configured the app runs in dev mode and returns a fixed
    local user, so everything works without auth in local development and tests.
    """
    if not settings.auth_enabled:
        return DEV_USER

    sealed = request.cookies.get(COOKIE_NAME)
    if not sealed:
        raise UnauthorizedError("Not authenticated.")

    user, refreshed = await auth.load_user(sealed)
    if user is None:
        raise UnauthorizedError("Session expired or invalid.")
    if refreshed:
        set_session_cookie(response, refreshed, settings)
    return UserRead(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        profile_picture_url=user.profile_picture_url,
    )
